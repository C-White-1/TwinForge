PROGRAM main
VAR
    CountPulse : BOOL AT %QX0.0;
    ResetCounter : BOOL AT %QX0.1;
    Done : BOOL AT %QX0.2;
    CurrentCount : DINT AT %MD0;

    CounterInstance : CTU_DINT;
    Preset : DINT := 3;
END_VAR

{
  "name": "main",
  "rungs": [
    {
      "id": "rung_main_5dca8b20-d109-4e39-adcf-004a60b5ca48",
      "comment": "",
      "defaultBounds": [
        300,
        100
      ],
      "reactFlowViewport": [
        659,
        174
      ],
      "nodes": [
        {
          "id": "left-rail-rung_main_5dca8b20-d109-4e39-adcf-004a60b5ca48",
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
            "numericId": "9802896",
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
          "id": "CONTACT_a50ecc64-bcc8-4b9f-a4e8-44b4cf5e4e98",
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
            "numericId": "4635552",
            "variable": {
              "name": "CountPulse",
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
          "id": "BLOCK_88a3e3da-69c0-4b32-9157-6740fc94b46a",
          "type": "block",
          "position": {
            "x": 257,
            "y": 14
          },
          "height": 140,
          "width": 96,
          "measured": {
            "width": 96,
            "height": 140
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
                "id": "CU",
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
                "id": "R",
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
                "id": "PV",
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
                  "x": 353,
                  "y": 50
                },
                "relPosition": {
                  "x": 96,
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
                  "x": 353,
                  "y": 90
                },
                "relPosition": {
                  "x": 96,
                  "y": 76
                },
                "id": "CV",
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
                  "x": 257,
                  "y": 50
                },
                "relPosition": {
                  "x": 0,
                  "y": 36
                },
                "id": "CU",
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
                "id": "R",
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
                "id": "PV",
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
                  "x": 353,
                  "y": 50
                },
                "relPosition": {
                  "x": 96,
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
                  "x": 353,
                  "y": 90
                },
                "relPosition": {
                  "x": 96,
                  "y": 76
                },
                "id": "CV",
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
                "x": 257,
                "y": 50
              },
              "relPosition": {
                "x": 0,
                "y": 36
              },
              "id": "CU",
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
                "x": 353,
                "y": 50
              },
              "relPosition": {
                "x": 96,
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
            "numericId": "10233022",
            "variant": {
              "name": "CTU_DINT",
              "type": "function-block",
              "language": "st",
              "variables": [
                {
                  "name": "CU",
                  "class": "input",
                  "type": {
                    "definition": "base-type",
                    "value": "BOOL"
                  }
                },
                {
                  "name": "R",
                  "class": "input",
                  "type": {
                    "definition": "base-type",
                    "value": "BOOL"
                  }
                },
                {
                  "name": "PV",
                  "class": "input",
                  "type": {
                    "definition": "base-type",
                    "value": "DINT"
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
                  "name": "CV",
                  "class": "output",
                  "type": {
                    "definition": "base-type",
                    "value": "DINT"
                  }
                },
                {
                  "name": "CU_T",
                  "class": "local",
                  "type": {
                    "definition": "derived-type",
                    "value": "R_TRIG"
                  }
                }
              ],
              "body": "CU_T(CU);\n        IF R THEN CV := 0;\n        ELSIF CU_T.Q AND (CV < PV) THEN CV := CV+1;\n        END_IF;\n        Q := (CV >= PV);",
              "documentation": "The up-counter can be used to signal when a count has reached a maximum value."
            },
            "variable": {
              "name": "CounterInstance",
              "class": "local",
              "type": {
                "definition": "derived",
                "value": "CTU_DINT"
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
                "handleId": "R",
                "type": "input",
                "variable": {
                  "name": "ResetCounter",
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
                "handleId": "PV",
                "type": "input",
                "variable": {
                  "name": "Preset",
                  "class": "local",
                  "type": {
                    "definition": "base-type",
                    "value": "dint"
                  },
                  "location": "",
                  "initialValue": "3",
                  "documentation": "",
                  "debug": false
                }
              },
              {
                "handleId": "CV",
                "type": "output",
                "variable": {
                  "name": "CurrentCount",
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
              }
            ],
            "draggable": true,
            "selectable": true,
            "deletable": true,
            "hasDivergence": false
          }
        },
        {
          "id": "COIL_98b2cb0f-aa6c-4c06-b70f-a8a9e0036244",
          "type": "coil",
          "position": {
            "x": 518,
            "y": 38
          },
          "height": 24,
          "width": 28,
          "measured": {
            "width": 28,
            "height": 24
          },
          "draggable": false,
          "selectable": true,
          "data": {
            "handles": [
              {
                "glbPosition": {
                  "x": 518,
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
                  "x": 546,
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
                  "x": 518,
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
                  "x": 546,
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
                "x": 518,
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
                "x": 546,
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
            "numericId": "4036913",
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
            "deletable": true
          }
        },
        {
          "id": "right-rail-rung_main_5dca8b20-d109-4e39-adcf-004a60b5ca48",
          "type": "powerRail",
          "position": {
            "x": 656,
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
                "x": 656
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
            "numericId": "8394917",
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
          "id": "VARIABLE_c0e6c970-d13d-434b-bf68-05dc7cf1aebf",
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
            "numericId": "4155516",
            "variable": {
              "name": "ResetCounter",
              "class": "local",
              "type": {
                "definition": "base-type",
                "value": "bool"
              },
              "location": "%QX0.1",
              "initialValue": null,
              "documentation": "",
              "debug": false
            },
            "executionOrder": 0,
            "variant": "input",
            "block": {
              "id": "BLOCK_88a3e3da-69c0-4b32-9157-6740fc94b46a",
              "handleId": "R",
              "variableType": {
                "name": "R",
                "class": "input",
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
          "id": "VARIABLE_5f962390-4c68-4132-83f1-35b49ee337f8",
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
            "numericId": "6810674",
            "variable": {
              "name": "Preset",
              "class": "local",
              "type": {
                "definition": "base-type",
                "value": "dint"
              },
              "location": "",
              "initialValue": "3",
              "documentation": "",
              "debug": false
            },
            "executionOrder": 0,
            "variant": "input",
            "block": {
              "id": "BLOCK_88a3e3da-69c0-4b32-9157-6740fc94b46a",
              "handleId": "PV",
              "variableType": {
                "name": "PV",
                "class": "input",
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
        },
        {
          "id": "VARIABLE_df935806-d305-496d-b006-686ba9d6b0ce",
          "type": "variable",
          "position": {
            "x": 383,
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
                  "x": 383,
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
                  "x": 383,
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
                "x": 383,
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
            "numericId": "4000859",
            "variable": {
              "name": "CurrentCount",
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
              "id": "BLOCK_88a3e3da-69c0-4b32-9157-6740fc94b46a",
              "handleId": "CV",
              "variableType": {
                "name": "CV",
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
          "id": "e_left-rail-rung_main_5dca8b20-d109-4e39-adcf-004a60b5ca48_CONTACT_a50ecc64-bcc8-4b9f-a4e8-44b4cf5e4e98__left-rail_input",
          "source": "left-rail-rung_main_5dca8b20-d109-4e39-adcf-004a60b5ca48",
          "sourceHandle": "left-rail",
          "target": "CONTACT_a50ecc64-bcc8-4b9f-a4e8-44b4cf5e4e98",
          "targetHandle": "input"
        },
        {
          "id": "e_CONTACT_a50ecc64-bcc8-4b9f-a4e8-44b4cf5e4e98_BLOCK_88a3e3da-69c0-4b32-9157-6740fc94b46a__output_CU",
          "source": "CONTACT_a50ecc64-bcc8-4b9f-a4e8-44b4cf5e4e98",
          "sourceHandle": "output",
          "target": "BLOCK_88a3e3da-69c0-4b32-9157-6740fc94b46a",
          "targetHandle": "CU"
        },
        {
          "id": "e_BLOCK_88a3e3da-69c0-4b32-9157-6740fc94b46a_COIL_98b2cb0f-aa6c-4c06-b70f-a8a9e0036244__Q_input",
          "source": "BLOCK_88a3e3da-69c0-4b32-9157-6740fc94b46a",
          "sourceHandle": "Q",
          "target": "COIL_98b2cb0f-aa6c-4c06-b70f-a8a9e0036244",
          "targetHandle": "input"
        },
        {
          "id": "e_COIL_98b2cb0f-aa6c-4c06-b70f-a8a9e0036244_right-rail-rung_main_5dca8b20-d109-4e39-adcf-004a60b5ca48__output_right-rail",
          "source": "COIL_98b2cb0f-aa6c-4c06-b70f-a8a9e0036244",
          "sourceHandle": "output",
          "target": "right-rail-rung_main_5dca8b20-d109-4e39-adcf-004a60b5ca48",
          "targetHandle": "right-rail"
        },
        {
          "id": "e_VARIABLE_c0e6c970-d13d-434b-bf68-05dc7cf1aebf_BLOCK_88a3e3da-69c0-4b32-9157-6740fc94b46a__output_R",
          "source": "VARIABLE_c0e6c970-d13d-434b-bf68-05dc7cf1aebf",
          "sourceHandle": "output",
          "target": "BLOCK_88a3e3da-69c0-4b32-9157-6740fc94b46a",
          "targetHandle": "R"
        },
        {
          "id": "e_VARIABLE_5f962390-4c68-4132-83f1-35b49ee337f8_BLOCK_88a3e3da-69c0-4b32-9157-6740fc94b46a__output_PV",
          "source": "VARIABLE_5f962390-4c68-4132-83f1-35b49ee337f8",
          "sourceHandle": "output",
          "target": "BLOCK_88a3e3da-69c0-4b32-9157-6740fc94b46a",
          "targetHandle": "PV"
        },
        {
          "id": "e_BLOCK_88a3e3da-69c0-4b32-9157-6740fc94b46a_VARIABLE_df935806-d305-496d-b006-686ba9d6b0ce__CV_input",
          "source": "BLOCK_88a3e3da-69c0-4b32-9157-6740fc94b46a",
          "sourceHandle": "CV",
          "target": "VARIABLE_df935806-d305-496d-b006-686ba9d6b0ce",
          "targetHandle": "input"
        }
      ]
    }
  ]
}
END_PROGRAM