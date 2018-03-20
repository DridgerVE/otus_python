package main

import (
	"os"
	"path/filepath"
	"flag"
	"log"
	"runtime"
	"sort"
	"sync"
	"compress/gzip"
	"time"
	"bufio"
	"strings"
	"strconv"
	"github.com/bradfitz/gomemcache/memcache"
	"github.com/golang/protobuf/proto"
	"appsinstalled"
	"fmt"
)

const(
	NORMAL_ERR_RATE = 0.01
	MEMCACHE_TIMEOUT = 1 * time.Second
)

type (
	proto_msg struct {
		key   string
		value []byte
	}
)

var (
	device_memc map[string] *string
	pattern *string
	//logfile *string
)

func main()  {
	var group sync.WaitGroup
	device_memc = make(map[string] *string)
	device_memc["idfa"] = flag.String("idfa", "127.0.0.1:33013", "memcache-0")
	device_memc["gaid"] = flag.String("gaid", "127.0.0.1:33014", "memcache-1")
	device_memc["adid"] = flag.String("adid", "127.0.0.1:33015", "memcache-2")
	device_memc["dvid"] = flag.String("dvid", "127.0.0.1:33016", "memcache-3")
	pattern = flag.String( "pattern", "./data/*.tsv.gz", "pattern files")
	//logfile = flag.String("log", "memc_load.log", "logfile")
	log.SetOutput(os.Stdout)
	flag.Parse()
	if *pattern == "" {
		log.Fatal("Empty pattern files")
	}
	runtime.GOMAXPROCS(runtime.NumCPU())
	files, e := filepath.Glob(*pattern)
	if e != nil {
		log.Println("Pattern error:", e)
		os.Exit(1)
	}
	sort.Strings(files)
	for _, file := range files {
		name := filepath.Base(file)
		if strings.HasPrefix(name, "."){
			continue
		}
		group.Add(1)
		go process_handler(file, device_memc, &group)
	}
	group.Wait()
	for _, file := range files {
		name := filepath.Base(file)
		if !strings.HasPrefix(name, ".") {
			dot_rename(file)
			log.Println("Rename file:", file)
		}
	}
}

func process_handler(file string, device_memc map[string] *string, group *sync.WaitGroup){
	var (
		//line_processing sync.WaitGroup
		insert_memc sync.WaitGroup
		parse_line sync.WaitGroup
		processed int
		errors_cnt int
	)
	defer group.Done()
	log.Println("Processing file", file)
	f, e := os.Open(file)
	if e != nil {
		log.Println("File open error:", file, e)
		return
	}
	defer f.Close()

	fd, e :=  gzip.NewReader(f)
	if e != nil{
		log.Println("Gzip error", file, e)
		return
	}
	defer fd.Close()

	proto_msgs := make(map[string] chan *proto_msg)
	memcaches := make(map[string] *memcache.Client)
	errors := make(chan int, len(device_memc) * 2)
	lines := make(chan string, len(device_memc))
	for device_type, addr := range device_memc{
		memcaches[device_type] = memcache.New(*addr)
		memcaches[device_type].Timeout = MEMCACHE_TIMEOUT
		//memcaches[device_type].MaxIdleConns = 100
		insert_memc.Add(1)
		proto_msgs[device_type] = make(chan *proto_msg)
		go insert_appsinstalled(memcaches[device_type], proto_msgs[device_type], errors, &insert_memc)
		parse_line.Add(1)
		go parse_appsinstalled(lines, device_memc, proto_msgs, errors, &parse_line)
	}
	scanner := bufio.NewScanner(fd)
	for scanner.Scan() {
		line := scanner.Text()
		lines <- line
		processed += 1
	}
	close(lines)

	parse_line.Wait()
	for _, msgs := range proto_msgs {
		close(msgs)
	}
	insert_memc.Wait()

	close(errors)

	for e := range errors{
		errors_cnt += e
	}

	if processed > 0 {
		err_rate := float64(errors_cnt) / float64(processed)
		if err_rate < NORMAL_ERR_RATE {
			log.Printf("Processing: %d record, ascceptable error rate (%f). Successfull load: %s", processed, err_rate, file)
		} else {
			log.Printf("Processing: %d record, high error rate (%f > %f). Failed load: %s" ,processed, err_rate, NORMAL_ERR_RATE, file)
		}
	}
}

func parse_appsinstalled(lines chan string, device_memc map[string] *string, msgs map[string](chan *proto_msg),
	errors chan int, line_processing *sync.WaitGroup){
	defer line_processing.Done()
	err := 0
	for line := range lines {
		var apps []uint32
		line_parts := strings.Split(line, "\t")
		if len(line_parts) != 5 {
			log.Println("Format error:", line)
			err++
			continue
		}
		device_type := line_parts[0]

		if _, ok := device_memc[device_type]; !ok {
			log.Println("Unsupported device type:", device_type)
			err++
			continue
		}
		device_id := line_parts[1]
		lat, e := strconv.ParseFloat(line_parts[2], 64)
		if e != nil {
			log.Println("Latitude error: ", line)
			err++
			continue
		}
		lon, e := strconv.ParseFloat(line_parts[3], 64)
		if e != nil {
			log.Println("Longitude error: ", line)
			err++
			continue
		}
		apps_parts := strings.Split(line_parts[4], ",")
		for _, app := range apps_parts {
			a, e := strconv.ParseUint(app, 10, 32)
			if e != nil {
				continue
			}
			apps = append(apps, uint32(a))
		}
		apps_installed := appsinstalled.UserApps{
			Apps: apps,
			Lat:  &lat,
			Lon:  &lon,
		}
		value, e := proto.Marshal(&apps_installed)
		if e != nil {
			log.Println("Can't encode protobuf message: ", line)
			err++
			continue
		}
		key := fmt.Sprintf("%s:%s", device_type, device_id)
		msg := proto_msg{
			key:   key,
			value: value,
		}
		msgs[device_type] <- &msg
	}
	errors <- err
}

func insert_appsinstalled(memc *memcache.Client, msgs chan *proto_msg, errors chan int, insert_memc *sync.WaitGroup) {
	defer insert_memc.Done()
	err := 0
	attempts := 5
	delay := 0.2
	cur_attempt := 1
	for msg := range msgs {
		e := memc.Set(&memcache.Item{Key: msg.key, Value: msg.value})
		for {
			if e == nil || cur_attempt == attempts {
				break
			}
			time.Sleep(time.Second * time.Duration(delay))
			cur_attempt++
			e = memc.Set(&memcache.Item{Key: msg.key, Value: msg.value})
		}
		if e != nil {
			log.Println("Memcache error: ", e)
			err += 1
		} else {
			attempts = 5
			cur_attempt = 1
		}

	}
	errors <- err
}

func dot_rename(oldname string) error {
	return os.Rename(oldname, filepath.Join(filepath.Dir(oldname),  "." + filepath.Base(oldname)))
}