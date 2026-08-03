PROGRAM main
VAR
    Enable : BOOL AT %QX0.0;
    ResetTimer : BOOL AT %QX0.1;
    Done : BOOL AT %QX0.2;

    RetentiveTimer : TF_RTO;
    Preset : TIME := T#5s;
    ElapsedTime : TIME;
    ElapsedSeconds : DINT AT %MD0;
    TimerEnabled : BOOL AT %QX0.3;
    TimerTiming : BOOL AT %QX0.4;
END_VAR

{
  "name": "main",
  "rungs": [
    {
      "id": "rung_main_6eed622d-4848-460d-af4e-a39fc04059ec",
      "comment": "",
      "defaultBounds": [
        300,
        100
      ],
      "reactFlowViewport": [
        725,
        214
      ],
      "nodes": [
        {
          "id": "left-rail-rung_main_6eed622d-4848-460d-af4e-a39fc04059ec",
          "type": "powerRail",
          "position": {
            "x": 0,
            "y": 30
          },
          "height": 40,
          "width": 3,
          "measured": {
            "width": 3,
            "height": 40
          },
          "draggable": false,
          "selectable": false,
          "data": {
            "handles": [
              {
                "glbPosition": {
                  "x": 3,
                  "y": 50
                },
                "relPosition": {
                  "x": 3,
                  "y": 20
                },
                "id": "left-rail",
                "position": "right",
                "type": "source",
                "isConnectable": false,
                "style": {
                  "top": 20,
                  "right": -3
                }
              }
            ],
            "inputHandles": [],
            "outputHandles": [
              {
                "glbPosition": {
                  "x": 3,
                  "y": 50
                },
                "relPosition": {
                  "x": 3,
                  "y": 20
                },
                "id": "left-rail",
                "position": "right",
                "type": "source",
                "isConnectable": false,
                "style": {
                  "top": 20,
                  "right": -3
                }
              }
            ],
            "outputConnector": {
              "glbPosition": {
                "x": 3,
                "y": 50
              },
              "relPosition": {
                "x": 3,
                "y": 20
              },
              "id": "left-rail",
              "position": "right",
              "type": "source",
              "isConnectable": false,
              "style": {
                "top": 20,
                "right": -3
              }
            },
            "numericId": "10392343",
            "variant": "left",
            "variable": {
              "name": ""
            },
            "executionOrder": 0,
            "draggable": false,
            "selectable": false,
            "deletable": false,
            "hasDivergence": false
          }
        },
        {
          "id": "CONTACT_10005d2a-16e5-447b-9a8b-6844c0360bde",
          "type": "contact",
          "position": {
            "x": 68,
            "y": 38
          },
          "height": 24,
          "width": 24,
          "measured": {
            "width": 24,
            "height": 24
          },
          "draggable": true,
          "selectable": true,
          "data": {
            "handles": [
              {
                "glbPosition": {
                  "x": 68,
                  "y": 50
                },
                "relPosition": {
                  "x": 0,
                  "y": 12
                },
                "id": "input",
                "position": "left",
                "isConnectable": false,
                "type": "target",
                "style": {
                  "left": -3
                }
              },
              {
                "glbPosition": {
                  "x": 92,
                  "y": 50
                },
                "relPosition": {
                  "x": 24,
                  "y": 12
                },
                "id": "output",
                "position": "right",
                "isConnectable": false,
                "type": "source",
                "style": {
                  "right": -3
                }
              }
            ],
            "variant": "default",
            "inputHandles": [
              {
                "glbPosition": {
                  "x": 68,
                  "y": 50
                },
                "relPosition": {
                  "x": 0,
                  "y": 12
                },
                "id": "input",
                "position": "left",
                "isConnectable": false,
                "type": "target",
                "style": {
                  "left": -3
                }
              }
            ],
            "outputHandles": [
              {
                "glbPosition": {
                  "x": 92,
                  "y": 50
                },
                "relPosition": {
                  "x": 24,
                  "y": 12
                },
                "id": "output",
                "position": "right",
                "isConnectable": false,
                "type": "source",
                "style": {
                  "right": -3
                }
              }
            ],
            "inputConnector": {
              "glbPosition": {
                "x": 68,
                "y": 50
              },
              "relPosition": {
                "x": 0,
                "y": 12
              },
              "id": "input",
              "position": "left",
              "isConnectable": false,
              "type": "target",
              "style": {
                "left": -3
              }
            },
            "outputConnector": {
              "glbPosition": {
                "x": 92,
                "y": 50
              },
              "relPosition": {
                "x": 24,
                "y": 12
              },
              "id": "output",
              "position": "right",
              "isConnectable": false,
              "type": "source",
              "style": {
                "right": -3
              }
            },
            "numericId": "8996356",
            "variable": {
              "name": "Enable",
              "class": "local",
              "type": {
                "definition": "base-type",
                "value": "bool"
              },
              "location": "%QX0.0",
              "initialValue": null,
              "documentation": "",
              "debug": false
            },
            "executionOrder": 0,
            "draggable": true,
            "selectable": true,
            "deletable": true,
            "hasDivergence": false
          }
        },
        {
          "id": "BLOCK_93709450-e988-4e83-ba95-95b6723fd79f",
          "type": "block",
          "position": {
            "x": 257,
            "y": 14
          },
          "height": 180,
          "width": 162,
          "measured": {
            "width": 162,
            "height": 180
          },
          "draggable": true,
          "selectable": true,
          "data": {
            "handles": [
              {
                "glbPosition": {
                  "x": 257,
                  "y": 50
                },
                "relPosition": {
                  "x": 0,
                  "y": 36
                },
                "id": "IN",
                "position": "left",
                "type": "target",
                "isConnectable": false,
                "style": {
                  "top": 36,
                  "left": 0
                }
              },
              {
                "glbPosition": {
                  "x": 257,
                  "y": 90
                },
                "relPosition": {
                  "x": 0,
                  "y": 76
                },
                "id": "RESET",
                "position": "left",
                "type": "target",
                "isConnectable": false,
                "style": {
                  "top": 76,
                  "left": 0
                }
              },
              {
                "glbPosition": {
                  "x": 257,
                  "y": 130
                },
                "relPosition": {
                  "x": 0,
                  "y": 116
                },
                "id": "PT",
                "position": "left",
                "type": "target",
                "isConnectable": false,
                "style": {
                  "top": 116,
                  "left": 0
                }
              },
              {
                "glbPosition": {
                  "x": 419,
                  "y": 50
                },
                "relPosition": {
                  "x": 162,
                  "y": 36
                },
                "id": "Q",
                "position": "right",
                "type": "source",
                "isConnectable": false,
                "style": {
                  "top": 36,
                  "right": 0
                }
              },
              {
                "glbPosition": {
                  "x": 419,
                  "y": 90
                },
                "relPosition": {
                  "x": 162,
                  "y": 76
                },
                "id": "ET",
                "position": "right",
                "type": "source",
                "isConnectable": false,
                "style": {
                  "top": 76,
                  "right": 0
                }
              },
              {
                "glbPosition": {
                  "x": 419,
                  "y": 130
                },
                "relPosition": {
                  "x": 162,
                  "y": 116
                },
                "id": "Enabled",
                "position": "right",
                "type": "source",
                "isConnectable": false,
                "style": {
                  "top": 116,
                  "right": 0
                }
              },
              {
                "glbPosition": {
                  "x": 419,
                  "y": 170
                },
                "relPosition": {
                  "x": 162,
                  "y": 156
                },
                "id": "TT",
                "position": "right",
                "type": "source",
                "isConnectable": false,
                "style": {
                  "top": 156,
                  "right": 0
                }
              }
            ],
            "inputHandles": [
              {
                "glbPosition": {
                  "x": 257,
                  "y": 50
                },
                "relPosition": {
                  "x": 0,
                  "y": 36
                },
                "id": "IN",
                "position": "left",
                "type": "target",
                "isConnectable": false,
                "style": {
                  "top": 36,
                  "left": 0
                }
              },
              {
                "glbPosition": {
                  "x": 257,
                  "y": 90
                },
                "relPosition": {
                  "x": 0,
                  "y": 76
                },
                "id": "RESET",
                "position": "left",
                "type": "target",
                "isConnectable": false,
                "style": {
                  "top": 76,
                  "left": 0
                }
              },
              {
                "glbPosition": {
                  "x": 257,
                  "y": 130
                },
                "relPosition": {
                  "x": 0,
                  "y": 116
                },
                "id": "PT",
                "position": "left",
                "type": "target",
                "isConnectable": false,
                "style": {
                  "top": 116,
                  "left": 0
                }
              }
            ],
            "outputHandles": [
              {
                "glbPosition": {
                  "x": 419,
                  "y": 50
                },
                "relPosition": {
                  "x": 162,
                  "y": 36
                },
                "id": "Q",
                "position": "right",
                "type": "source",
                "isConnectable": false,
                "style": {
                  "top": 36,
                  "right": 0
                }
              },
              {
                "glbPosition": {
                  "x": 419,
                  "y": 90
                },
                "relPosition": {
                  "x": 162,
                  "y": 76
                },
                "id": "ET",
                "position": "right",
                "type": "source",
                "isConnectable": false,
                "style": {
                  "top": 76,
                  "right": 0
                }
              },
              {
                "glbPosition": {
                  "x": 419,
                  "y": 130
                },
                "relPosition": {
                  "x": 162,
                  "y": 116
                },
                "id": "Enabled",
                "position": "right",
                "type": "source",
                "isConnectable": false,
                "style": {
                  "top": 116,
                  "right": 0
                }
              },
              {
                "glbPosition": {
                  "x": 419,
                  "y": 170
                },
                "relPosition": {
                  "x": 162,
                  "y": 156
                },
                "id": "TT",
                "position": "right",
                "type": "source",
                "isConnectable": false,
                "style": {
                  "top": 156,
                  "right": 0
                }
              }
            ],
            "inputConnector": {
              "glbPosition": {
                "x": 257,
                "y": 50
              },
              "relPosition": {
                "x": 0,
                "y": 36
              },
              "id": "IN",
              "position": "left",
              "type": "target",
              "isConnectable": false,
              "style": {
                "top": 36,
                "left": 0
              }
            },
            "outputConnector": {
              "glbPosition": {
                "x": 419,
                "y": 50
              },
              "relPosition": {
                "x": 162,
                "y": 36
              },
              "id": "Q",
              "position": "right",
              "type": "source",
              "isConnectable": false,
              "style": {
                "top": 36,
                "right": 0
              }
            },
            "numericId": "4378454",
            "variant": {
              "name": "TF_RTO",
              "type": "function-block",
              "variables": [
                {
                  "name": "IN",
                  "class": "input",
                  "type": {
                    "definition": "base-type",
                    "value": "BOOL"
                  }
                },
                {
                  "name": "RESET",
                  "class": "input",
                  "type": {
                    "definition": "base-type",
                    "value": "BOOL"
                  }
                },
                {
                  "name": "PT",
                  "class": "input",
                  "type": {
                    "definition": "base-type",
                    "value": "TIME"
                  }
                },
                {
                  "name": "Q",
                  "class": "output",
                  "type": {
                    "definition": "base-type",
                    "value": "BOOL"
                  }
                },
                {
                  "name": "ET",
                  "class": "output",
                  "type": {
                    "definition": "base-type",
                    "value": "TIME"
                  }
                },
                {
                  "name": "Enabled",
                  "class": "output",
                  "type": {
                    "definition": "base-type",
                    "value": "BOOL"
                  }
                },
                {
                  "name": "TT",
                  "class": "output",
                  "type": {
                    "definition": "base-type",
                    "value": "BOOL"
                  }
                },
                {
                  "name": "SegmentTimer",
                  "class": "local",
                  "type": {
                    "definition": "derived",
                    "value": "TON"
                  }
                },
                {
                  "name": "RetainedTime",
                  "class": "local",
                  "type": {
                    "definition": "base-type",
                    "value": "TIME"
                  }
                },
                {
                  "name": "RemainingTime",
                  "class": "local",
                  "type": {
                    "definition": "base-type",
                    "value": "TIME"
                  }
                },
                {
                  "name": "WasEnabled",
                  "class": "local",
                  "type": {
                    "definition": "base-type",
                    "value": "BOOL"
                  }
                }
              ],
              "documentation": "",
              "extensible": false
            },
            "variable": {
              "name": "RetentiveTimer",
              "class": "local",
              "type": {
                "definition": "derived",
                "value": "TF_RTO"
              },
              "location": "",
              "initialValue": null,
              "documentation": "",
              "debug": false
            },
            "executionOrder": 0,
            "executionControl": false,
            "lockExecutionControl": false,
            "connectedVariables": [
              {
                "handleId": "RESET",
                "type": "input",
                "variable": {
                  "name": "ResetTimer",
                  "class": "local",
                  "type": {
                    "definition": "base-type",
                    "value": "bool"
                  },
                  "location": "%QX0.1",
                  "initialValue": null,
                  "documentation": "",
                  "debug": false
                }
              },
              {
                "handleId": "PT",
                "type": "input",
                "variable": {
                  "name": "Preset",
                  "class": "local",
                  "type": {
                    "definition": "base-type",
                    "value": "time"
                  },
                  "location": "",
                  "initialValue": "T#5s",
                  "documentation": "",
                  "debug": false
                }
              },
              {
                "handleId": "TT",
                "type": "output",
                "variable": {
                  "name": "TimerTiming",
                  "class": "local",
                  "type": {
                    "definition": "base-type",
                    "value": "bool"
                  },
                  "location": "%QX0.4",
                  "initialValue": null,
                  "documentation": "",
                  "debug": false
                }
              },
              {
                "handleId": "Enabled",
                "type": "output",
                "variable": {
                  "name": "TimerEnabled",
                  "class": "local",
                  "type": {
                    "definition": "base-type",
                    "value": "bool"
                  },
                  "location": "%QX0.3",
                  "initialValue": null,
                  "documentation": "",
                  "debug": false
                }
              },
              {
                "handleId": "ET",
                "type": "output",
                "variable": {
                  "name": "ElapsedTime",
                  "class": "local",
                  "type": {
                    "definition": "base-type",
                    "value": "time"
                  },
                  "location": "",
                  "initialValue": null,
                  "documentation": "",
                  "debug": false
                }
              }
            ],
            "draggable": true,
            "selectable": true,
            "deletable": true
          }
        },
        {
          "id": "COIL_e83bd71f-3169-40e3-8fd6-c87b1aa351a0",
          "type": "coil",
          "position": {
            "x": 584,
            "y": 38
          },
          "height": 24,
          "width": 28,
          "measured": {
            "width": 28,
            "height": 24
          },
          "draggable": true,
          "selectable": true,
          "data": {
            "handles": [
              {
                "glbPosition": {
                  "x": 584,
                  "y": 50
                },
                "relPosition": {
                  "x": 0,
                  "y": 12
                },
                "id": "input",
                "position": "left",
                "isConnectable": false,
                "type": "target",
                "style": {
                  "left": -3
                }
              },
              {
                "glbPosition": {
                  "x": 612,
                  "y": 50
                },
                "relPosition": {
                  "x": 28,
                  "y": 12
                },
                "id": "output",
                "position": "right",
                "isConnectable": false,
                "type": "source",
                "style": {
                  "right": -3
                }
              }
            ],
            "variant": "default",
            "inputHandles": [
              {
                "glbPosition": {
                  "x": 584,
                  "y": 50
                },
                "relPosition": {
                  "x": 0,
                  "y": 12
                },
                "id": "input",
                "position": "left",
                "isConnectable": false,
                "type": "target",
                "style": {
                  "left": -3
                }
              }
            ],
            "outputHandles": [
              {
                "glbPosition": {
                  "x": 612,
                  "y": 50
                },
                "relPosition": {
                  "x": 28,
                  "y": 12
                },
                "id": "output",
                "position": "right",
                "isConnectable": false,
                "type": "source",
                "style": {
                  "right": -3
                }
              }
            ],
            "inputConnector": {
              "glbPosition": {
                "x": 584,
                "y": 50
              },
              "relPosition": {
                "x": 0,
                "y": 12
              },
              "id": "input",
              "position": "left",
              "isConnectable": false,
              "type": "target",
              "style": {
                "left": -3
              }
            },
            "outputConnector": {
              "glbPosition": {
                "x": 612,
                "y": 50
              },
              "relPosition": {
                "x": 28,
                "y": 12
              },
              "id": "output",
              "position": "right",
              "isConnectable": false,
              "type": "source",
              "style": {
                "right": -3
              }
            },
            "numericId": "3752410",
            "variable": {
              "name": "Done",
              "class": "local",
              "type": {
                "definition": "base-type",
                "value": "bool"
              },
              "location": "%QX0.2",
              "initialValue": null,
              "documentation": "",
              "debug": false
            },
            "executionOrder": 0,
            "draggable": true,
            "selectable": true,
            "deletable": true,
            "hasDivergence": false
          }
        },
        {
          "id": "right-rail-rung_main_6eed622d-4848-460d-af4e-a39fc04059ec",
          "type": "powerRail",
          "position": {
            "x": 722,
            "y": 30
          },
          "height": 40,
          "width": 3,
          "measured": {
            "width": 3,
            "height": 40
          },
          "draggable": false,
          "selectable": false,
          "data": {
            "handles": [
              {
                "glbPosition": {
                  "x": 297,
                  "y": 50
                },
                "relPosition": {
                  "x": 3,
                  "y": 20
                },
                "id": "right-rail",
                "position": "left",
                "type": "target",
                "isConnectable": false,
                "style": {
                  "top": 20,
                  "left": -3
                },
                "x": 722
              }
            ],
            "inputHandles": [
              {
                "glbPosition": {
                  "x": 297,
                  "y": 50
                },
                "relPosition": {
                  "x": 3,
                  "y": 20
                },
                "id": "right-rail",
                "position": "left",
                "type": "target",
                "isConnectable": false,
                "style": {
                  "top": 20,
                  "left": -3
                }
              }
            ],
            "outputHandles": [],
            "inputConnector": {
              "glbPosition": {
                "x": 297,
                "y": 50
              },
              "relPosition": {
                "x": 3,
                "y": 20
              },
              "id": "right-rail",
              "position": "left",
              "type": "target",
              "isConnectable": false,
              "style": {
                "top": 20,
                "left": -3
              }
            },
            "numericId": "741464",
            "variant": "right",
            "variable": {
              "name": ""
            },
            "executionOrder": 0,
            "draggable": false,
            "selectable": false,
            "deletable": false,
            "hasDivergence": false
          }
        },
        {
          "id": "VARIABLE_8130578b-e607-4a1b-be49-d0fdce11fb77",
          "type": "variable",
          "position": {
            "x": 147,
            "y": 74
          },
          "height": 32,
          "width": 80,
          "measured": {
            "width": 80,
            "height": 32
          },
          "draggable": false,
          "selectable": true,
          "data": {
            "handles": [
              {
                "glbPosition": {
                  "x": 307,
                  "y": 90
                },
                "relPosition": {
                  "x": 80,
                  "y": 16
                },
                "id": "output",
                "position": "right",
                "isConnectable": false,
                "type": "source"
              }
            ],
            "inputHandles": [],
            "outputHandles": [
              {
                "glbPosition": {
                  "x": 307,
                  "y": 90
                },
                "relPosition": {
                  "x": 80,
                  "y": 16
                },
                "id": "output",
                "position": "right",
                "isConnectable": false,
                "type": "source"
              }
            ],
            "outputConnector": {
              "glbPosition": {
                "x": 307,
                "y": 90
              },
              "relPosition": {
                "x": 80,
                "y": 16
              },
              "id": "output",
              "position": "right",
              "isConnectable": false,
              "type": "source"
            },
            "numericId": "9760844",
            "variable": {
              "name": "ResetTimer",
              "class": "local",
              "type": {
                "definition": "base-type",
                "value": "bool"
              },
              "location": "%QX0.1",
              "initialValue": null,
              "documentation": "",
              "debug": false,
              "id": "broken-VARIABLE_8130578b-e607-4a1b-be49-d0fdce11fb77"
            },
            "executionOrder": 0,
            "variant": "input",
            "block": {
              "id": "BLOCK_93709450-e988-4e83-ba95-95b6723fd79f",
              "handleId": "RESET",
              "variableType": {
                "name": "RESET",
                "class": "input",
                "type": {
                  "definition": "base-type",
                  "value": "BOOL"
                }
              }
            },
            "draggable": false,
            "selectable": true,
            "deletable": false,
            "wrongVariable": true
          }
        },
        {
          "id": "VARIABLE_1620d55e-4ddf-46ca-8848-1e7254a94e76",
          "type": "variable",
          "position": {
            "x": 147,
            "y": 114
          },
          "height": 32,
          "width": 80,
          "measured": {
            "width": 80,
            "height": 32
          },
          "draggable": false,
          "selectable": true,
          "data": {
            "handles": [
              {
                "glbPosition": {
                  "x": 307,
                  "y": 130
                },
                "relPosition": {
                  "x": 80,
                  "y": 16
                },
                "id": "output",
                "position": "right",
                "isConnectable": false,
                "type": "source"
              }
            ],
            "inputHandles": [],
            "outputHandles": [
              {
                "glbPosition": {
                  "x": 307,
                  "y": 130
                },
                "relPosition": {
                  "x": 80,
                  "y": 16
                },
                "id": "output",
                "position": "right",
                "isConnectable": false,
                "type": "source"
              }
            ],
            "outputConnector": {
              "glbPosition": {
                "x": 307,
                "y": 130
              },
              "relPosition": {
                "x": 80,
                "y": 16
              },
              "id": "output",
              "position": "right",
              "isConnectable": false,
              "type": "source"
            },
            "numericId": "3947270",
            "variable": {
              "name": "Preset",
              "class": "local",
              "type": {
                "definition": "base-type",
                "value": "time"
              },
              "location": "",
              "initialValue": "T#5s",
              "documentation": "",
              "debug": false,
              "id": "broken-VARIABLE_1620d55e-4ddf-46ca-8848-1e7254a94e76"
            },
            "executionOrder": 0,
            "variant": "input",
            "block": {
              "id": "BLOCK_93709450-e988-4e83-ba95-95b6723fd79f",
              "handleId": "PT",
              "variableType": {
                "name": "PT",
                "class": "input",
                "type": {
                  "definition": "base-type",
                  "value": "TIME"
                }
              }
            },
            "draggable": false,
            "selectable": true,
            "deletable": false,
            "wrongVariable": true
          }
        },
        {
          "id": "VARIABLE_fd2fe205-d489-43b0-a6f9-a6d4b3a536cc",
          "type": "variable",
          "position": {
            "x": 449,
            "y": 74
          },
          "height": 32,
          "width": 80,
          "measured": {
            "width": 80,
            "height": 32
          },
          "draggable": false,
          "selectable": true,
          "data": {
            "handles": [
              {
                "glbPosition": {
                  "x": 449,
                  "y": 90
                },
                "relPosition": {
                  "x": 0,
                  "y": 16
                },
                "id": "input",
                "position": "left",
                "isConnectable": false,
                "type": "target"
              }
            ],
            "inputHandles": [
              {
                "glbPosition": {
                  "x": 449,
                  "y": 90
                },
                "relPosition": {
                  "x": 0,
                  "y": 16
                },
                "id": "input",
                "position": "left",
                "isConnectable": false,
                "type": "target"
              }
            ],
            "outputHandles": [],
            "inputConnector": {
              "glbPosition": {
                "x": 449,
                "y": 90
              },
              "relPosition": {
                "x": 0,
                "y": 16
              },
              "id": "input",
              "position": "left",
              "isConnectable": false,
              "type": "target"
            },
            "numericId": "7643979",
            "variable": {
              "name": "ElapsedTime",
              "class": "local",
              "type": {
                "definition": "base-type",
                "value": "time"
              },
              "location": "",
              "initialValue": null,
              "documentation": "",
              "debug": false
            },
            "executionOrder": 0,
            "variant": "output",
            "block": {
              "id": "BLOCK_93709450-e988-4e83-ba95-95b6723fd79f",
              "handleId": "ET",
              "variableType": {
                "name": "ET",
                "class": "output",
                "type": {
                  "definition": "base-type",
                  "value": "TIME"
                }
              }
            },
            "draggable": false,
            "selectable": true,
            "deletable": false
          }
        },
        {
          "id": "VARIABLE_b10df9e7-7c23-4487-8fb2-1d30faa876a9",
          "type": "variable",
          "position": {
            "x": 449,
            "y": 114
          },
          "height": 32,
          "width": 80,
          "measured": {
            "width": 80,
            "height": 32
          },
          "draggable": false,
          "selectable": true,
          "data": {
            "handles": [
              {
                "glbPosition": {
                  "x": 449,
                  "y": 130
                },
                "relPosition": {
                  "x": 0,
                  "y": 16
                },
                "id": "input",
                "position": "left",
                "isConnectable": false,
                "type": "target"
              }
            ],
            "inputHandles": [
              {
                "glbPosition": {
                  "x": 449,
                  "y": 130
                },
                "relPosition": {
                  "x": 0,
                  "y": 16
                },
                "id": "input",
                "position": "left",
                "isConnectable": false,
                "type": "target"
              }
            ],
            "outputHandles": [],
            "inputConnector": {
              "glbPosition": {
                "x": 449,
                "y": 130
              },
              "relPosition": {
                "x": 0,
                "y": 16
              },
              "id": "input",
              "position": "left",
              "isConnectable": false,
              "type": "target"
            },
            "numericId": "4964309",
            "variable": {
              "name": "TimerEnabled",
              "class": "local",
              "type": {
                "definition": "base-type",
                "value": "bool"
              },
              "location": "%QX0.3",
              "initialValue": null,
              "documentation": "",
              "debug": false
            },
            "executionOrder": 0,
            "variant": "output",
            "block": {
              "id": "BLOCK_93709450-e988-4e83-ba95-95b6723fd79f",
              "handleId": "Enabled",
              "variableType": {
                "name": "Enabled",
                "class": "output",
                "type": {
                  "definition": "base-type",
                  "value": "BOOL"
                }
              }
            },
            "draggable": false,
            "selectable": true,
            "deletable": false
          }
        },
        {
          "id": "VARIABLE_777173a1-1b1a-4348-802f-1f7a3e1e6b87",
          "type": "variable",
          "position": {
            "x": 449,
            "y": 154
          },
          "height": 32,
          "width": 80,
          "measured": {
            "width": 80,
            "height": 32
          },
          "draggable": false,
          "selectable": true,
          "data": {
            "handles": [
              {
                "glbPosition": {
                  "x": 449,
                  "y": 170
                },
                "relPosition": {
                  "x": 0,
                  "y": 16
                },
                "id": "input",
                "position": "left",
                "isConnectable": false,
                "type": "target"
              }
            ],
            "inputHandles": [
              {
                "glbPosition": {
                  "x": 449,
                  "y": 170
                },
                "relPosition": {
                  "x": 0,
                  "y": 16
                },
                "id": "input",
                "position": "left",
                "isConnectable": false,
                "type": "target"
              }
            ],
            "outputHandles": [],
            "inputConnector": {
              "glbPosition": {
                "x": 449,
                "y": 170
              },
              "relPosition": {
                "x": 0,
                "y": 16
              },
              "id": "input",
              "position": "left",
              "isConnectable": false,
              "type": "target"
            },
            "numericId": "6714730",
            "variable": {
              "name": "TimerTiming",
              "class": "local",
              "type": {
                "definition": "base-type",
                "value": "bool"
              },
              "location": "%QX0.4",
              "initialValue": null,
              "documentation": "",
              "debug": false
            },
            "executionOrder": 0,
            "variant": "output",
            "block": {
              "id": "BLOCK_93709450-e988-4e83-ba95-95b6723fd79f",
              "handleId": "TT",
              "variableType": {
                "name": "TT",
                "class": "output",
                "type": {
                  "definition": "base-type",
                  "value": "BOOL"
                }
              }
            },
            "draggable": false,
            "selectable": true,
            "deletable": false
          }
        }
      ],
      "edges": [
        {
          "id": "e_left-rail-rung_main_6eed622d-4848-460d-af4e-a39fc04059ec_CONTACT_10005d2a-16e5-447b-9a8b-6844c0360bde__left-rail_input",
          "source": "left-rail-rung_main_6eed622d-4848-460d-af4e-a39fc04059ec",
          "sourceHandle": "left-rail",
          "target": "CONTACT_10005d2a-16e5-447b-9a8b-6844c0360bde",
          "targetHandle": "input"
        },
        {
          "id": "e_COIL_e83bd71f-3169-40e3-8fd6-c87b1aa351a0_right-rail-rung_main_6eed622d-4848-460d-af4e-a39fc04059ec__output_right-rail",
          "source": "COIL_e83bd71f-3169-40e3-8fd6-c87b1aa351a0",
          "sourceHandle": "output",
          "target": "right-rail-rung_main_6eed622d-4848-460d-af4e-a39fc04059ec",
          "targetHandle": "right-rail"
        },
        {
          "id": "e_CONTACT_10005d2a-16e5-447b-9a8b-6844c0360bde_BLOCK_93709450-e988-4e83-ba95-95b6723fd79f__output_???",
          "source": "CONTACT_10005d2a-16e5-447b-9a8b-6844c0360bde",
          "sourceHandle": "output",
          "target": "BLOCK_93709450-e988-4e83-ba95-95b6723fd79f",
          "targetHandle": "IN"
        },
        {
          "id": "e_BLOCK_93709450-e988-4e83-ba95-95b6723fd79f_COIL_e83bd71f-3169-40e3-8fd6-c87b1aa351a0__???_input",
          "source": "BLOCK_93709450-e988-4e83-ba95-95b6723fd79f",
          "sourceHandle": "Q",
          "target": "COIL_e83bd71f-3169-40e3-8fd6-c87b1aa351a0",
          "targetHandle": "input"
        },
        {
          "id": "e_VARIABLE_8130578b-e607-4a1b-be49-d0fdce11fb77_BLOCK_93709450-e988-4e83-ba95-95b6723fd79f__output_RESET",
          "source": "VARIABLE_8130578b-e607-4a1b-be49-d0fdce11fb77",
          "sourceHandle": "output",
          "target": "BLOCK_93709450-e988-4e83-ba95-95b6723fd79f",
          "targetHandle": "RESET"
        },
        {
          "id": "e_VARIABLE_1620d55e-4ddf-46ca-8848-1e7254a94e76_BLOCK_93709450-e988-4e83-ba95-95b6723fd79f__output_PT",
          "source": "VARIABLE_1620d55e-4ddf-46ca-8848-1e7254a94e76",
          "sourceHandle": "output",
          "target": "BLOCK_93709450-e988-4e83-ba95-95b6723fd79f",
          "targetHandle": "PT"
        },
        {
          "id": "e_BLOCK_93709450-e988-4e83-ba95-95b6723fd79f_VARIABLE_fd2fe205-d489-43b0-a6f9-a6d4b3a536cc__ET_input",
          "source": "BLOCK_93709450-e988-4e83-ba95-95b6723fd79f",
          "sourceHandle": "ET",
          "target": "VARIABLE_fd2fe205-d489-43b0-a6f9-a6d4b3a536cc",
          "targetHandle": "input"
        },
        {
          "id": "e_BLOCK_93709450-e988-4e83-ba95-95b6723fd79f_VARIABLE_b10df9e7-7c23-4487-8fb2-1d30faa876a9__Enabled_input",
          "source": "BLOCK_93709450-e988-4e83-ba95-95b6723fd79f",
          "sourceHandle": "Enabled",
          "target": "VARIABLE_b10df9e7-7c23-4487-8fb2-1d30faa876a9",
          "targetHandle": "input"
        },
        {
          "id": "e_BLOCK_93709450-e988-4e83-ba95-95b6723fd79f_VARIABLE_777173a1-1b1a-4348-802f-1f7a3e1e6b87__TT_input",
          "source": "BLOCK_93709450-e988-4e83-ba95-95b6723fd79f",
          "sourceHandle": "TT",
          "target": "VARIABLE_777173a1-1b1a-4348-802f-1f7a3e1e6b87",
          "targetHandle": "input"
        }
      ]
    },
    {
      "id": "rung_main_3971a6de-028c-42f9-919d-8df2b670a786",
      "comment": "",
      "defaultBounds": [
        300,
        100
      ],
      "reactFlowViewport": [
        550,
        134
      ],
      "nodes": [
        {
          "id": "left-rail-rung_main_3971a6de-028c-42f9-919d-8df2b670a786",
          "type": "powerRail",
          "position": {
            "x": 0,
            "y": 30
          },
          "height": 40,
          "width": 3,
          "measured": {
            "width": 3,
            "height": 40
          },
          "draggable": false,
          "selectable": false,
          "data": {
            "handles": [
              {
                "glbPosition": {
                  "x": 3,
                  "y": 50
                },
                "relPosition": {
                  "x": 3,
                  "y": 20
                },
                "id": "left-rail",
                "position": "right",
                "type": "source",
                "isConnectable": false,
                "style": {
                  "top": 20,
                  "right": -3
                }
              }
            ],
            "inputHandles": [],
            "outputHandles": [
              {
                "glbPosition": {
                  "x": 3,
                  "y": 50
                },
                "relPosition": {
                  "x": 3,
                  "y": 20
                },
                "id": "left-rail",
                "position": "right",
                "type": "source",
                "isConnectable": false,
                "style": {
                  "top": 20,
                  "right": -3
                }
              }
            ],
            "outputConnector": {
              "glbPosition": {
                "x": 3,
                "y": 50
              },
              "relPosition": {
                "x": 3,
                "y": 20
              },
              "id": "left-rail",
              "position": "right",
              "type": "source",
              "isConnectable": false,
              "style": {
                "top": 20,
                "right": -3
              }
            },
            "numericId": "1648044",
            "variant": "left",
            "variable": {
              "name": ""
            },
            "executionOrder": 0,
            "draggable": false,
            "selectable": false,
            "deletable": false,
            "hasDivergence": false
          }
        },
        {
          "id": "BLOCK_c7d7d691-288d-4ee0-8795-25244424f1e8",
          "type": "block",
          "position": {
            "x": 143,
            "y": 14
          },
          "height": 100,
          "width": 144,
          "measured": {
            "width": 144,
            "height": 100
          },
          "draggable": true,
          "selectable": true,
          "data": {
            "handles": [
              {
                "glbPosition": {
                  "x": 143,
                  "y": 50
                },
                "relPosition": {
                  "x": 0,
                  "y": 36
                },
                "id": "EN",
                "position": "left",
                "type": "target",
                "isConnectable": false,
                "style": {
                  "top": 36,
                  "left": 0
                }
              },
              {
                "glbPosition": {
                  "x": 143,
                  "y": 90
                },
                "relPosition": {
                  "x": 0,
                  "y": 76
                },
                "id": "IN",
                "position": "left",
                "type": "target",
                "isConnectable": false,
                "style": {
                  "top": 76,
                  "left": 0
                }
              },
              {
                "glbPosition": {
                  "x": 287,
                  "y": 50
                },
                "relPosition": {
                  "x": 144,
                  "y": 36
                },
                "id": "ENO",
                "position": "right",
                "type": "source",
                "isConnectable": false,
                "style": {
                  "top": 36,
                  "right": 0
                }
              },
              {
                "glbPosition": {
                  "x": 287,
                  "y": 90
                },
                "relPosition": {
                  "x": 144,
                  "y": 76
                },
                "id": "OUT",
                "position": "right",
                "type": "source",
                "isConnectable": false,
                "style": {
                  "top": 76,
                  "right": 0
                }
              }
            ],
            "inputHandles": [
              {
                "glbPosition": {
                  "x": 143,
                  "y": 50
                },
                "relPosition": {
                  "x": 0,
                  "y": 36
                },
                "id": "EN",
                "position": "left",
                "type": "target",
                "isConnectable": false,
                "style": {
                  "top": 36,
                  "left": 0
                }
              },
              {
                "glbPosition": {
                  "x": 143,
                  "y": 90
                },
                "relPosition": {
                  "x": 0,
                  "y": 76
                },
                "id": "IN",
                "position": "left",
                "type": "target",
                "isConnectable": false,
                "style": {
                  "top": 76,
                  "left": 0
                }
              }
            ],
            "outputHandles": [
              {
                "glbPosition": {
                  "x": 287,
                  "y": 50
                },
                "relPosition": {
                  "x": 144,
                  "y": 36
                },
                "id": "ENO",
                "position": "right",
                "type": "source",
                "isConnectable": false,
                "style": {
                  "top": 36,
                  "right": 0
                }
              },
              {
                "glbPosition": {
                  "x": 287,
                  "y": 90
                },
                "relPosition": {
                  "x": 144,
                  "y": 76
                },
                "id": "OUT",
                "position": "right",
                "type": "source",
                "isConnectable": false,
                "style": {
                  "top": 76,
                  "right": 0
                }
              }
            ],
            "inputConnector": {
              "glbPosition": {
                "x": 143,
                "y": 50
              },
              "relPosition": {
                "x": 0,
                "y": 36
              },
              "id": "EN",
              "position": "left",
              "type": "target",
              "isConnectable": false,
              "style": {
                "top": 36,
                "left": 0
              }
            },
            "outputConnector": {
              "glbPosition": {
                "x": 287,
                "y": 50
              },
              "relPosition": {
                "x": 144,
                "y": 36
              },
              "id": "ENO",
              "position": "right",
              "type": "source",
              "isConnectable": false,
              "style": {
                "top": 36,
                "right": 0
              }
            },
            "numericId": "6461353",
            "variant": {
              "name": "TIME_TO_DINT",
              "type": "function",
              "language": "st",
              "variables": [
                {
                  "name": "EN",
                  "class": "input",
                  "type": {
                    "definition": "base-type",
                    "value": "BOOL"
                  }
                },
                {
                  "name": "ENO",
                  "class": "output",
                  "type": {
                    "definition": "base-type",
                    "value": "BOOL"
                  }
                },
                {
                  "name": "OUT",
                  "class": "output",
                  "type": {
                    "definition": "base-type",
                    "value": "DINT"
                  }
                },
                {
                  "name": "IN",
                  "class": "input",
                  "type": {
                    "definition": "base-type",
                    "value": "TIME"
                  }
                }
              ],
              "body": "Data type conversion",
              "documentation": "(IN: TIME) => OUT: DINT",
              "extensible": false
            },
            "variable": {
              "name": ""
            },
            "executionOrder": 0,
            "executionControl": true,
            "lockExecutionControl": true,
            "connectedVariables": [
              {
                "handleId": "OUT",
                "type": "output",
                "variable": {
                  "name": "ElapsedSeconds",
                  "class": "local",
                  "type": {
                    "definition": "base-type",
                    "value": "dint"
                  },
                  "location": "%MD0",
                  "initialValue": null,
                  "documentation": "",
                  "debug": false
                }
              },
              {
                "handleId": "IN",
                "type": "input",
                "variable": {
                  "name": "ElapsedTime",
                  "class": "local",
                  "type": {
                    "definition": "base-type",
                    "value": "time"
                  },
                  "location": "",
                  "initialValue": null,
                  "documentation": "",
                  "debug": false
                }
              }
            ],
            "draggable": true,
            "selectable": true,
            "deletable": true
          }
        },
        {
          "id": "right-rail-rung_main_3971a6de-028c-42f9-919d-8df2b670a786",
          "type": "powerRail",
          "position": {
            "x": 547,
            "y": 30
          },
          "height": 40,
          "width": 3,
          "measured": {
            "width": 3,
            "height": 40
          },
          "draggable": false,
          "selectable": false,
          "data": {
            "handles": [
              {
                "glbPosition": {
                  "x": 297,
                  "y": 50
                },
                "relPosition": {
                  "x": 3,
                  "y": 20
                },
                "id": "right-rail",
                "position": "left",
                "type": "target",
                "isConnectable": false,
                "style": {
                  "top": 20,
                  "left": -3
                },
                "x": 547
              }
            ],
            "inputHandles": [
              {
                "glbPosition": {
                  "x": 297,
                  "y": 50
                },
                "relPosition": {
                  "x": 3,
                  "y": 20
                },
                "id": "right-rail",
                "position": "left",
                "type": "target",
                "isConnectable": false,
                "style": {
                  "top": 20,
                  "left": -3
                }
              }
            ],
            "outputHandles": [],
            "inputConnector": {
              "glbPosition": {
                "x": 297,
                "y": 50
              },
              "relPosition": {
                "x": 3,
                "y": 20
              },
              "id": "right-rail",
              "position": "left",
              "type": "target",
              "isConnectable": false,
              "style": {
                "top": 20,
                "left": -3
              }
            },
            "numericId": "5956869",
            "variant": "right",
            "variable": {
              "name": ""
            },
            "executionOrder": 0,
            "draggable": false,
            "selectable": false,
            "deletable": false,
            "hasDivergence": false
          }
        },
        {
          "id": "VARIABLE_b6543fd0-3cc1-4765-8fbc-ab5e4e5e99aa",
          "type": "variable",
          "position": {
            "x": 33,
            "y": 74
          },
          "height": 32,
          "width": 80,
          "measured": {
            "width": 80,
            "height": 32
          },
          "draggable": false,
          "selectable": true,
          "data": {
            "handles": [
              {
                "glbPosition": {
                  "x": 193,
                  "y": 90
                },
                "relPosition": {
                  "x": 80,
                  "y": 16
                },
                "id": "output",
                "position": "right",
                "isConnectable": false,
                "type": "source"
              }
            ],
            "inputHandles": [],
            "outputHandles": [
              {
                "glbPosition": {
                  "x": 193,
                  "y": 90
                },
                "relPosition": {
                  "x": 80,
                  "y": 16
                },
                "id": "output",
                "position": "right",
                "isConnectable": false,
                "type": "source"
              }
            ],
            "outputConnector": {
              "glbPosition": {
                "x": 193,
                "y": 90
              },
              "relPosition": {
                "x": 80,
                "y": 16
              },
              "id": "output",
              "position": "right",
              "isConnectable": false,
              "type": "source"
            },
            "numericId": "3613374",
            "variable": {
              "name": "ElapsedTime",
              "class": "local",
              "type": {
                "definition": "base-type",
                "value": "time"
              },
              "location": "",
              "initialValue": null,
              "documentation": "",
              "debug": false
            },
            "executionOrder": 0,
            "variant": "input",
            "block": {
              "id": "BLOCK_c7d7d691-288d-4ee0-8795-25244424f1e8",
              "handleId": "IN",
              "variableType": {
                "name": "IN",
                "class": "input",
                "type": {
                  "definition": "base-type",
                  "value": "TIME"
                }
              }
            },
            "draggable": false,
            "selectable": true,
            "deletable": false
          }
        },
        {
          "id": "VARIABLE_977e8ad9-606d-4610-b1c2-eb66a46ba91a",
          "type": "variable",
          "position": {
            "x": 317,
            "y": 74
          },
          "height": 32,
          "width": 80,
          "measured": {
            "width": 80,
            "height": 32
          },
          "draggable": false,
          "selectable": true,
          "data": {
            "handles": [
              {
                "glbPosition": {
                  "x": 317,
                  "y": 90
                },
                "relPosition": {
                  "x": 0,
                  "y": 16
                },
                "id": "input",
                "position": "left",
                "isConnectable": false,
                "type": "target"
              }
            ],
            "inputHandles": [
              {
                "glbPosition": {
                  "x": 317,
                  "y": 90
                },
                "relPosition": {
                  "x": 0,
                  "y": 16
                },
                "id": "input",
                "position": "left",
                "isConnectable": false,
                "type": "target"
              }
            ],
            "outputHandles": [],
            "inputConnector": {
              "glbPosition": {
                "x": 317,
                "y": 90
              },
              "relPosition": {
                "x": 0,
                "y": 16
              },
              "id": "input",
              "position": "left",
              "isConnectable": false,
              "type": "target"
            },
            "numericId": "1364816",
            "variable": {
              "name": "ElapsedSeconds",
              "class": "local",
              "type": {
                "definition": "base-type",
                "value": "dint"
              },
              "location": "%MD0",
              "initialValue": null,
              "documentation": "",
              "debug": false
            },
            "executionOrder": 0,
            "variant": "output",
            "block": {
              "id": "BLOCK_c7d7d691-288d-4ee0-8795-25244424f1e8",
              "handleId": "OUT",
              "variableType": {
                "name": "OUT",
                "class": "output",
                "type": {
                  "definition": "base-type",
                  "value": "DINT"
                }
              }
            },
            "draggable": false,
            "selectable": true,
            "deletable": false
          }
        }
      ],
      "edges": [
        {
          "id": "e_left-rail-rung_main_3971a6de-028c-42f9-919d-8df2b670a786_BLOCK_c7d7d691-288d-4ee0-8795-25244424f1e8__left-rail_EN",
          "source": "left-rail-rung_main_3971a6de-028c-42f9-919d-8df2b670a786",
          "sourceHandle": "left-rail",
          "target": "BLOCK_c7d7d691-288d-4ee0-8795-25244424f1e8",
          "targetHandle": "EN"
        },
        {
          "id": "e_BLOCK_c7d7d691-288d-4ee0-8795-25244424f1e8_right-rail-rung_main_3971a6de-028c-42f9-919d-8df2b670a786__ENO_right-rail",
          "source": "BLOCK_c7d7d691-288d-4ee0-8795-25244424f1e8",
          "sourceHandle": "ENO",
          "target": "right-rail-rung_main_3971a6de-028c-42f9-919d-8df2b670a786",
          "targetHandle": "right-rail"
        },
        {
          "id": "e_VARIABLE_b6543fd0-3cc1-4765-8fbc-ab5e4e5e99aa_BLOCK_c7d7d691-288d-4ee0-8795-25244424f1e8__output_IN",
          "source": "VARIABLE_b6543fd0-3cc1-4765-8fbc-ab5e4e5e99aa",
          "sourceHandle": "output",
          "target": "BLOCK_c7d7d691-288d-4ee0-8795-25244424f1e8",
          "targetHandle": "IN"
        },
        {
          "id": "e_BLOCK_c7d7d691-288d-4ee0-8795-25244424f1e8_VARIABLE_977e8ad9-606d-4610-b1c2-eb66a46ba91a__OUT_input",
          "source": "BLOCK_c7d7d691-288d-4ee0-8795-25244424f1e8",
          "sourceHandle": "OUT",
          "target": "VARIABLE_977e8ad9-606d-4610-b1c2-eb66a46ba91a",
          "targetHandle": "input"
        }
      ]
    }
  ]
}
END_PROGRAM