{
  "fileFormat": 2,
  "featureLevel": 109,
  "creator": "zap",
  "keyValuePairs": [
    {
      "key": "commandDiscovery",
      "value": "1"
    },
    {
      "key": "defaultResponsePolicy",
      "value": "always"
    },
    {
      "key": "manufacturerCodes",
      "value": "0x1049"
    }
  ],
  "package": [
    {
      "pathRelativity": "relativeToZap",
      "path": "..\\..\\..\\..\\..\\..\\..\\Users\\mnowak\\.silabs\\slt\\installs\\conan\\p\\simpl1a11563c2e399\\p\\zigbee\\app\\zcl\\zcl-zap.json",
      "type": "zcl-properties",
      "category": "zigbee",
      "version": 1,
      "description": "Zigbee Silabs ZCL data"
    },
    {
      "pathRelativity": "relativeToZap",
      "path": "..\\..\\..\\..\\..\\..\\..\\Users\\mnowak\\.silabs\\slt\\installs\\conan\\p\\simpl1a11563c2e399\\p\\zigbee\\app\\framework\\gen-template\\gen-templates.json",
      "type": "gen-templates-json",
      "category": "zigbee",
      "version": "zigbee-v0"
    }
  ],
  "endpointTypes": [
    {
      "id": 1,
      "name": "Anonymous Endpoint Type",
      "deviceTypeRef": {
        "code": 770,
        "profileId": 260,
        "label": "HA-tempsensor",
        "name": "HA-tempsensor",
        "deviceTypeOrder": 0
      },
      "deviceTypes": [
        {
          "code": 770,
          "profileId": 260,
          "label": "HA-tempsensor",
          "name": "HA-tempsensor",
          "deviceTypeOrder": 0
        }
      ],
      "deviceVersions": [
        1
      ],
      "deviceIdentifiers": [
        770
      ],
      "deviceTypeName": "HA-tempsensor",
      "deviceTypeCode": 770,
      "deviceTypeProfileId": 260,
      "clusters": [
        {
          "name": "Basic",
          "code": 0,
          "mfgCode": null,
          "define": "BASIC_CLUSTER",
          "side": "server",
          "enabled": 1,
          "attributes": [
            {
              "name": "ZCL version",
              "code": 0,
              "mfgCode": null,
              "side": "server",
              "type": "int8u",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 1,
              "bounded": null,
              "defaultValue": "8",
              "reportable": 0,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 0
            },
            {
              "name": "manufacturer name",
              "code": 4,
              "mfgCode": null,
              "side": "server",
              "type": "char_string",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 1,
              "bounded": null,
              "defaultValue": "nowaControl",
              "reportable": 0,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 0
            },
            {
              "name": "model identifier",
              "code": 5,
              "mfgCode": null,
              "side": "server",
              "type": "char_string",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 1,
              "bounded": null,
              "defaultValue": "Hydraulic Sensor V1",
              "reportable": 0,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 0
            },
            {
              "name": "power source",
              "code": 7,
              "mfgCode": null,
              "side": "server",
              "type": "enum8",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 1,
              "bounded": null,
              "defaultValue": "0",
              "reportable": 0,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 0
            },
            {
              "name": "SW build ID",
              "code": 16384,
              "mfgCode": null,
              "side": "server",
              "type": "char_string",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 1,
              "bounded": null,
              "defaultValue": "2026.04.01-1.0",
              "reportable": 0,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 0
            },
            {
              "name": "cluster revision",
              "code": 65533,
              "mfgCode": null,
              "side": "server",
              "type": "int16u",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 1,
              "bounded": null,
              "defaultValue": "3",
              "reportable": 0,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 0
            }
          ]
        },
        {
          "name": "Power Configuration",
          "code": 1,
          "mfgCode": null,
          "define": "POWER_CONFIG_CLUSTER",
          "side": "server",
          "enabled": 1,
          "attributes": [
            {
              "name": "cluster revision",
              "code": 65533,
              "mfgCode": null,
              "side": "server",
              "type": "int16u",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 1,
              "bounded": 0,
              "defaultValue": "2",
              "reportable": 0,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 0
            }
          ]
        },
        {
          "name": "Identify",
          "code": 3,
          "mfgCode": null,
          "define": "IDENTIFY_CLUSTER",
          "side": "client",
          "enabled": 1,
          "commands": [
            {
              "name": "IdentifyQueryResponse",
              "code": 0,
              "mfgCode": null,
              "source": "server",
              "isIncoming": 1,
              "isEnabled": 1
            },
            {
              "name": "Identify",
              "code": 0,
              "mfgCode": null,
              "source": "client",
              "isIncoming": 0,
              "isEnabled": 1
            },
            {
              "name": "IdentifyQuery",
              "code": 1,
              "mfgCode": null,
              "source": "client",
              "isIncoming": 0,
              "isEnabled": 1
            }
          ],
          "attributes": [
            {
              "name": "cluster revision",
              "code": 65533,
              "mfgCode": null,
              "side": "client",
              "type": "int16u",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 0,
              "bounded": null,
              "defaultValue": "2",
              "reportable": 0,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 0
            }
          ]
        },
        {
          "name": "Identify",
          "code": 3,
          "mfgCode": null,
          "define": "IDENTIFY_CLUSTER",
          "side": "server",
          "enabled": 1,
          "commands": [
            {
              "name": "IdentifyQueryResponse",
              "code": 0,
              "mfgCode": null,
              "source": "server",
              "isIncoming": 0,
              "isEnabled": 1
            },
            {
              "name": "Identify",
              "code": 0,
              "mfgCode": null,
              "source": "client",
              "isIncoming": 1,
              "isEnabled": 1
            },
            {
              "name": "IdentifyQuery",
              "code": 1,
              "mfgCode": null,
              "source": "client",
              "isIncoming": 1,
              "isEnabled": 1
            }
          ],
          "attributes": [
            {
              "name": "identify time",
              "code": 0,
              "mfgCode": null,
              "side": "server",
              "type": "int16u",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 0,
              "bounded": null,
              "defaultValue": "0",
              "reportable": 0,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 0
            },
            {
              "name": "cluster revision",
              "code": 65533,
              "mfgCode": null,
              "side": "server",
              "type": "int16u",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 0,
              "bounded": null,
              "defaultValue": "2",
              "reportable": 0,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 0
            }
          ]
        },
        {
          "name": "Temperature Measurement",
          "code": 1026,
          "mfgCode": null,
          "define": "TEMP_MEASUREMENT_CLUSTER",
          "side": "server",
          "enabled": 1,
          "attributes": [
            {
              "name": "measured value",
              "code": 0,
              "mfgCode": null,
              "side": "server",
              "type": "int16s",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 0,
              "bounded": null,
              "defaultValue": "32768",
              "reportable": 1,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 0
            },
            {
              "name": "min measured value",
              "code": 1,
              "mfgCode": null,
              "side": "server",
              "type": "int16s",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 0,
              "bounded": null,
              "defaultValue": "32768",
              "reportable": 0,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 0
            },
            {
              "name": "max measured value",
              "code": 2,
              "mfgCode": null,
              "side": "server",
              "type": "int16s",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 0,
              "bounded": null,
              "defaultValue": "32768",
              "reportable": 0,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 0
            },
            {
              "name": "cluster revision",
              "code": 65533,
              "mfgCode": null,
              "side": "server",
              "type": "int16u",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 0,
              "bounded": null,
              "defaultValue": "3",
              "reportable": 0,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 0
            }
          ]
        },
        {
          "name": "NowaControl Config",
          "code": 64528,
          "mfgCode": null,
          "define": "NOWA_CONTROL_CONFIG_CLUSTER",
          "side": "server",
          "enabled": 1,
          "attributes": [
            {
              "name": "measurement interval ms",
              "code": 0,
              "mfgCode": null,
              "side": "server",
              "type": "int32u",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 0,
              "bounded": null,
              "defaultValue": "60000",
              "reportable": 1,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 1000
            },
            {
              "name": "vorlauf offset",
              "code": 1,
              "mfgCode": null,
              "side": "server",
              "type": "int16s",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 0,
              "bounded": null,
              "defaultValue": "0",
              "reportable": 1,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 5
            },
            {
              "name": "ruecklauf offset",
              "code": 2,
              "mfgCode": null,
              "side": "server",
              "type": "int16s",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 0,
              "bounded": null,
              "defaultValue": "0",
              "reportable": 1,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 5
            },
            {
              "name": "sensor count",
              "code": 3,
              "mfgCode": null,
              "side": "server",
              "type": "int8u",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 0,
              "bounded": null,
              "defaultValue": "0",
              "reportable": 1,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 1
            },
            {
              "name": "error count",
              "code": 4,
              "mfgCode": null,
              "side": "server",
              "type": "int16u",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 0,
              "bounded": null,
              "defaultValue": "0",
              "reportable": 1,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 1
            },
            {
              "name": "last status",
              "code": 5,
              "mfgCode": null,
              "side": "server",
              "type": "int8u",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 0,
              "bounded": null,
              "defaultValue": "0",
              "reportable": 1,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 1
            },
            {
              "name": "last update age",
              "code": 6,
              "mfgCode": null,
              "side": "server",
              "type": "int32u",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 0,
              "bounded": null,
              "defaultValue": "0",
              "reportable": 1,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 1
            },
            {
              "name": "antenna mode",
              "code": 7,
              "mfgCode": null,
              "side": "server",
              "type": "enum8",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 0,
              "bounded": null,
              "defaultValue": "1",
              "reportable": 1,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 1
            },
            {
              "name": "rescan request",
              "code": 8,
              "mfgCode": null,
              "side": "server",
              "type": "int32u",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 0,
              "bounded": null,
              "defaultValue": "0",
              "reportable": 1,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 1
            },
            {
              "name": "factory reset request",
              "code": 9,
              "mfgCode": null,
              "side": "server",
              "type": "int32u",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 0,
              "bounded": null,
              "defaultValue": "0",
              "reportable": 1,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 1
            },
            {
              "name": "cluster revision",
              "code": 65533,
              "mfgCode": null,
              "side": "server",
              "type": "int16u",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 0,
              "bounded": null,
              "defaultValue": "1",
              "reportable": 0,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 0
            }
          ]
        }
      ]
    },
    {
      "id": 2,
      "name": "Anonymous Endpoint Type",
      "deviceTypeRef": {
        "code": 770,
        "profileId": 260,
        "label": "HA-tempsensor",
        "name": "HA-tempsensor",
        "deviceTypeOrder": 0
      },
      "deviceTypes": [
        {
          "code": 770,
          "profileId": 260,
          "label": "HA-tempsensor",
          "name": "HA-tempsensor",
          "deviceTypeOrder": 0
        }
      ],
      "deviceVersions": [
        1
      ],
      "deviceIdentifiers": [
        770
      ],
      "deviceTypeName": "HA-tempsensor",
      "deviceTypeCode": 770,
      "deviceTypeProfileId": 260,
      "clusters": [
        {
          "name": "Basic",
          "code": 0,
          "mfgCode": null,
          "define": "BASIC_CLUSTER",
          "side": "server",
          "enabled": 1,
          "attributes": [
            {
              "name": "ZCL version",
              "code": 0,
              "mfgCode": null,
              "side": "server",
              "type": "int8u",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 1,
              "bounded": null,
              "defaultValue": "8",
              "reportable": 0,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 0
            },
            {
              "name": "power source",
              "code": 7,
              "mfgCode": null,
              "side": "server",
              "type": "enum8",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 1,
              "bounded": null,
              "defaultValue": "0",
              "reportable": 0,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 0
            },
            {
              "name": "cluster revision",
              "code": 65533,
              "mfgCode": null,
              "side": "server",
              "type": "int16u",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 1,
              "bounded": null,
              "defaultValue": "3",
              "reportable": 0,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 0
            }
          ]
        },
        {
          "name": "Identify",
          "code": 3,
          "mfgCode": null,
          "define": "IDENTIFY_CLUSTER",
          "side": "client",
          "enabled": 1,
          "commands": [
            {
              "name": "IdentifyQueryResponse",
              "code": 0,
              "mfgCode": null,
              "source": "server",
              "isIncoming": 1,
              "isEnabled": 1
            },
            {
              "name": "Identify",
              "code": 0,
              "mfgCode": null,
              "source": "client",
              "isIncoming": 0,
              "isEnabled": 1
            },
            {
              "name": "IdentifyQuery",
              "code": 1,
              "mfgCode": null,
              "source": "client",
              "isIncoming": 0,
              "isEnabled": 1
            }
          ],
          "attributes": [
            {
              "name": "cluster revision",
              "code": 65533,
              "mfgCode": null,
              "side": "client",
              "type": "int16u",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 0,
              "bounded": null,
              "defaultValue": "2",
              "reportable": 0,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 0
            }
          ]
        },
        {
          "name": "Identify",
          "code": 3,
          "mfgCode": null,
          "define": "IDENTIFY_CLUSTER",
          "side": "server",
          "enabled": 1,
          "commands": [
            {
              "name": "Identify",
              "code": 0,
              "mfgCode": null,
              "source": "client",
              "isIncoming": 1,
              "isEnabled": 1
            },
            {
              "name": "IdentifyQueryResponse",
              "code": 0,
              "mfgCode": null,
              "source": "server",
              "isIncoming": 0,
              "isEnabled": 1
            },
            {
              "name": "IdentifyQuery",
              "code": 1,
              "mfgCode": null,
              "source": "client",
              "isIncoming": 1,
              "isEnabled": 1
            }
          ],
          "attributes": [
            {
              "name": "identify time",
              "code": 0,
              "mfgCode": null,
              "side": "server",
              "type": "int16u",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 0,
              "bounded": null,
              "defaultValue": "0",
              "reportable": 0,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 0
            },
            {
              "name": "cluster revision",
              "code": 65533,
              "mfgCode": null,
              "side": "server",
              "type": "int16u",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 0,
              "bounded": null,
              "defaultValue": "2",
              "reportable": 0,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 0
            }
          ]
        },
        {
          "name": "Temperature Measurement",
          "code": 1026,
          "mfgCode": null,
          "define": "TEMP_MEASUREMENT_CLUSTER",
          "side": "server",
          "enabled": 1,
          "attributes": [
            {
              "name": "measured value",
              "code": 0,
              "mfgCode": null,
              "side": "server",
              "type": "int16s",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 0,
              "bounded": null,
              "defaultValue": "32768",
              "reportable": 1,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 0
            },
            {
              "name": "min measured value",
              "code": 1,
              "mfgCode": null,
              "side": "server",
              "type": "int16s",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 0,
              "bounded": null,
              "defaultValue": "32768",
              "reportable": 0,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 0
            },
            {
              "name": "max measured value",
              "code": 2,
              "mfgCode": null,
              "side": "server",
              "type": "int16s",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 0,
              "bounded": null,
              "defaultValue": "32768",
              "reportable": 0,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 0
            },
            {
              "name": "cluster revision",
              "code": 65533,
              "mfgCode": null,
              "side": "server",
              "type": "int16u",
              "included": 1,
              "storageOption": "RAM",
              "singleton": 0,
              "bounded": null,
              "defaultValue": "3",
              "reportable": 0,
              "minInterval": 1,
              "maxInterval": 65534,
              "reportableChange": 0
            }
          ]
        }
      ]
    }
  ],
  "endpoints": [
    {
      "endpointTypeName": "Anonymous Endpoint Type",
      "endpointTypeIndex": 0,
      "profileId": 260,
      "endpointId": 1,
      "networkId": 0,
      "parentEndpointIdentifier": null
    },
    {
      "endpointTypeName": "Anonymous Endpoint Type",
      "endpointTypeIndex": 1,
      "profileId": 260,
      "endpointId": 2,
      "networkId": 0,
      "parentEndpointIdentifier": null
    },
    {
      "endpointTypeName": "Anonymous Endpoint Type",
      "endpointTypeIndex": 1,
      "profileId": 260,
      "endpointId": 3,
      "networkId": 0,
      "parentEndpointIdentifier": null
    }
  ]
}
