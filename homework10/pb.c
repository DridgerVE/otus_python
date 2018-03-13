#include <Python.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <zlib.h>
#include "deviceapps.pb-c.h"

#define MAGIC  0xFFFFFFFF
#define DEVICE_APPS_TYPE 1

typedef struct pbheader_s {
    uint32_t magic;
    uint16_t type;
    uint16_t length;
} pbheader_t;

#define PBHEADER_INIT {MAGIC, 0, 0}

size_t proto_pack_and_writefile(PyObject *dict, gzFile fd) {
    DeviceApps msg = DEVICE_APPS__INIT;
    DeviceApps__Device device = DEVICE_APPS__DEVICE__INIT;
    void *buf;
    unsigned len;

    PyObject *device_type = PyDict_GetItemString(dict, "device");
    if (device_type == NULL || !PyDict_Check(device_type)) {
        PyErr_SetString(PyExc_ValueError, "ErrorType: 'device' not a dict");
        return 0;
    }

    PyObject *id = PyDict_GetItemString(device_type, "id");

    if (id == NULL || !PyString_Check(id)) {
        PyErr_SetString(PyExc_ValueError, "ErrorType: 'id' not a string");
        return 0;
    }
    device.has_id = 1;
    device.id.data = (uint8_t*) PyString_AsString(id);
    device.id.len = strlen(PyString_AsString(id));

    PyObject *type_id = PyDict_GetItemString(device_type, "type");
    if (type_id == NULL || !PyString_Check(type_id)) {
        PyErr_SetString(PyExc_ValueError, "ErrorType: 'type' not a string");
        return 0;
    }
    device.has_type = 1;
    device.type.data = (uint8_t*) PyString_AsString(type_id);
    device.type.len = strlen(PyString_AsString(type_id));

    msg.device = &device;

    PyObject *lat = PyDict_GetItemString(dict, "lat");
    if (lat != NULL){
        if (PyFloat_Check(lat)){
            msg.has_lat = 1;
            msg.lat = PyFloat_AsDouble(lat);
        }
        else{
            if (PyInt_Check(lat)){
                msg.has_lat = 1;
                msg.lat = PyInt_AsLong(lat);
            }
            else {
                PyErr_SetString(PyExc_ValueError, "ErrorType: 'lat' not a numeric");
                return 0;
            }
        }
    }
    PyObject *lon = PyDict_GetItemString(dict, "lon");
    if (lon != NULL){
        if (PyFloat_Check(lon)){
            msg.has_lon = 1;
            msg.lon = PyFloat_AsDouble(lon);
        }
        else{
            if (PyInt_Check(lon)){
                msg.has_lon = 1;
                msg.lon = PyInt_AsLong(lon);
            }
            else {
                PyErr_SetString(PyExc_ValueError, "ErrorType: 'lon' not a numeric");
                return 0;
            }
        }
    }
    PyObject *apps = PyDict_GetItemString(dict, "apps");
    if (apps == NULL || !PyList_Check(apps)) {
        PyErr_SetString(PyExc_ValueError, "ErrorType: 'apps' not a a list");
        return 0;
    }
    int i = 0;
    int n_apps = PySequence_Size(apps);
    msg.n_apps = n_apps;
    if (n_apps > 0) {
        msg.apps = malloc(sizeof(uint32_t) * msg.n_apps);
        if (!msg.apps) {
            PyErr_SetString(PyExc_ValueError, "Error: can't allocate memory");
            return 0;
        }
        while (n_apps > 0) {
            PyObject *app = PyList_GET_ITEM(apps, i);
            if (!PyInt_Check(app)) {
                PyErr_SetString(PyExc_ValueError, "ErrorType: 'app' not a integer");
                return 0;
            }
            msg.apps[i] = PyInt_AsLong(app);
            i++;
            n_apps--;
        }
    }

    len = device_apps__get_packed_size(&msg);

    buf = malloc(len);
    if (!buf) {
        PyErr_SetString(PyExc_ValueError, "Error: can't allocate memory");
        return 0;
    }

    device_apps__pack(&msg, buf);

    pbheader_t pbheader = PBHEADER_INIT;
    pbheader.magic = MAGIC;
    pbheader.type = DEVICE_APPS_TYPE;
    pbheader.length = len;

    gzwrite(fd, &pbheader, sizeof(pbheader)); // Write message header
    gzwrite(fd, buf, len); // Write protobuf message

    free(msg.apps);
    free(buf);
    return (len + sizeof(pbheader));
}

// Read iterator of Python dicts
// Pack them to DeviceApps protobuf and write to file with appropriate header
// Return number of written bytes as Python integer
static PyObject* py_deviceapps_xwrite_pb(PyObject* self, PyObject* args) {
    const char *path;
    int bytes_written = 0;
    PyObject *o;

    if (!PyArg_ParseTuple(args, "Os", &o, &path))
        return NULL;

    PyObject *iterator = PyObject_GetIter(o);

    if (iterator == NULL) {
        PyErr_SetString(PyExc_ValueError, "ErrorType: first argument not a iterator");
        return NULL;
    }

    gzFile fd = gzopen(path, "wb");

    if (fd == NULL) {
        PyErr_SetString(PyExc_ValueError, "Error: Can't open the file");
        return NULL;
    }
    PyObject *item;
    item = PyIter_Next(iterator);
    while (item != NULL) {
        if (!PyDict_Check(item)) {
            PyErr_SetString(PyExc_ValueError, "ErrorType: 'deviceapps' not a dict");
            gzclose(fd);
            return NULL;
        }

        size_t len;
        len = proto_pack_and_writefile(item, fd);
        if (!len) {
            gzclose(fd);
            return NULL;
        }
        bytes_written += len;
        item = PyIter_Next(iterator);
    }

    gzclose(fd);

    if (PyErr_Occurred()) {
        PyErr_SetString(PyExc_RuntimeError, "Unknown error");
        return NULL;
    }
    return Py_BuildValue("i", bytes_written);
}

// Unpack only messages with type == DEVICE_APPS_TYPE
// Return iterator of Python dicts
static PyObject* py_deviceapps_xread_pb(PyObject* self, PyObject* args) {
    const char* path;

    DeviceApps *msg;
    DeviceApps__Device *device;

    if (!PyArg_ParseTuple(args, "s", &path))
        return NULL;

    gzFile fd = gzopen(path, "rb");

    if (fd == NULL) {
        PyErr_SetString(PyExc_ValueError, "Error: Can't open the file");
        return NULL;
    }
    int status = 1;
    uint32_t magic;
    uint16_t type;
    uint16_t length;
    //printf("\nRead from: %s\n", path);
    //int cnt = 0;
    PyObject *result;
    result = PyList_New(0);
    while (status > 0){
        status = gzread(fd, &magic, 4);
        if (status != 4) break;

        status = gzread(fd, &type, 2);
        if (status != 2) break;

        status = gzread(fd, &length, 2);
        if (status != 2) break;

        uint8_t buf[length];
        status = gzread(fd, buf, length);

        if (status != length) break;
        if (magic != MAGIC || type != DEVICE_APPS_TYPE) continue;
        msg = device_apps__unpack (NULL, length, buf); // Deserialize the serialized data
        if (msg == NULL){
            Py_DECREF(result);
            gzclose(fd);
            PyErr_SetString(PyExc_ValueError, "Error: wrong protobuf msg");
            return NULL;
        }
        device = msg->device;
        //соберем dict
        PyObject *item;
        item = PyDict_New();
        //type и id device
        PyObject *dev;
        dev = PyDict_New();
        if (device->has_id){
            PyObject *id;
            id = PyString_FromStringAndSize((char*)device->id.data, device->id.len);
            if (PyDict_SetItemString(dev, "id", id) == -1){
                Py_DECREF(id);
                Py_DECREF(result);
                Py_DECREF(item);
                Py_DECREF(dev);
                gzclose(fd);
                PyErr_SetString(PyExc_ValueError, "Error: can't create dict object");
                return NULL;
            }
            Py_DECREF(id);
        }
        if (device->has_type){
            PyObject *type;
            type = PyString_FromStringAndSize((char*)device->type.data, device->type.len);
            if (PyDict_SetItemString(dev, "type", type) == -1){
                Py_DECREF(type);
                Py_DECREF(result);
                Py_DECREF(item);
                Py_DECREF(dev);
                gzclose(fd);
                PyErr_SetString(PyExc_ValueError, "Error: can't create dict object");
                return NULL;
            }
            Py_DECREF(type);
        }
        if (PyDict_SetItemString(item, "device", dev) == -1) {
            gzclose(fd);
            Py_DECREF(result);
            Py_DECREF(item);
            Py_DECREF(dev);
            PyErr_SetString(PyExc_ValueError, "Error: can't create dict object");
            return NULL;
        }
        // координаты, если есть
        if (msg->has_lat){
            PyObject *lat;
            lat = PyFloat_FromDouble(msg->lat);
            if (PyDict_SetItemString(item, "lat", lat) == -1) {
                Py_DECREF(lat);
                Py_DECREF(result);
                Py_DECREF(item);
                Py_DECREF(dev);
                gzclose(fd);
                PyErr_SetString(PyExc_ValueError, "Error: can't create dict object");
                return NULL;
            }
            Py_DECREF(lat);
        }
        if (msg->has_lon){
            PyObject *lon;
            lon = PyFloat_FromDouble(msg->lon);
            if (PyDict_SetItemString(item, "lon", lon) == -1) {
                Py_DECREF(lon);
                Py_DECREF(result);
                Py_DECREF(item);
                Py_DECREF(dev);
                gzclose(fd);
                PyErr_SetString(PyExc_ValueError, "Error: can't create dict object");
                return NULL;
            }
            Py_DECREF(lon);
        }
        // добавим список apps
        PyObject *apps;
        apps = PyList_New(0);
        int i = 0;
        while (i < msg->n_apps) {
            PyObject *app;
            app = PyInt_FromLong(msg->apps[i]);
            if (PyList_Append(apps, app) == -1){
                Py_DECREF(app);
                Py_DECREF(result);
                Py_DECREF(item);
                Py_DECREF(dev);
                Py_DECREF(apps);
                gzclose(fd);
                PyErr_SetString(PyExc_ValueError, "Error: can't create list object");
                return NULL;
            }
            Py_DECREF(app);
            i = i + 1;
        }
        if (PyDict_SetItemString(item, "apps", apps) == -1) {
            gzclose(fd);
            Py_DECREF(result);
            Py_DECREF(item);
            Py_DECREF(dev);
            Py_DECREF(apps);
            PyErr_SetString(PyExc_ValueError, "Error: can't create dict object");
            return NULL;
        }
        Py_DECREF(apps);
        if (PyList_Append(result, item) == -1){
            Py_DECREF(result);
            Py_DECREF(item);
            Py_DECREF(dev);
            Py_DECREF(item);
            gzclose(fd);
            PyErr_SetString(PyExc_ValueError, "Error: can't create list object");
            return NULL;
        }
        Py_DECREF(item);
        //cnt = cnt + 1;
    }
    gzclose(fd);
    //printf("Count records %d\n", cnt);
    return result;
    //Py_RETURN_NONE;
}


static PyMethodDef PBMethods[] = {
     {"deviceapps_xwrite_pb", py_deviceapps_xwrite_pb, METH_VARARGS, "Write serialized protobuf to file from iterator"},
     {"deviceapps_xread_pb", py_deviceapps_xread_pb, METH_VARARGS, "Deserialize protobuf from file, return iterator"},
     {NULL, NULL, 0, NULL}
};


PyMODINIT_FUNC initpb(void) {
     (void) Py_InitModule("pb", PBMethods);
}
