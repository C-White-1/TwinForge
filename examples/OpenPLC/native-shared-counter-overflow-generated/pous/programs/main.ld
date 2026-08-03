PROGRAM main
VAR
	CountPulse : bool AT %QX0.0;
	CountDown : bool AT %QX0.1;
	ResetCounter : bool AT %QX0.2;
	Done : bool AT %QX0.3;
	PartCounter : TF_COUNTER;
	PartCounter_ACC : DINT AT %MD0;
	PartCounter_OV : BOOL AT %QX0.4;
	PartCounter_UN : BOOL AT %QX0.5;
END_VAR

{
  "name": "main",
  "rungs": [
    {
      "id": "rung_main_b1629c6d-2e3a-5aa0-943f-0c250f8c3ff3",
      "comment": "",
      "defaultBounds": [
        300,
        100
      ],
      "reactFlowViewport": [
        763,
        454
      ],
      "nodes": [
        {
          "id": "left-rail-rung_main_b1629c6d-2e3a-5aa0-943f-0c250f8c3ff3",
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
                "isConnectable": false,
                "type": "source",
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
                "isConnectable": false,
                "type": "source",
                "style": {
                  "top": 20,
                  "right": -3
                }
              }
            ],
            "numericId": "7626401",
            "variant": "left",
            "variable": {
              "name": ""
            },
            "executionOrder": 0,
            "draggable": false,
            "selectable": false,
            "deletable": false,
            "hasDivergence": false,
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
              "isConnectable": false,
              "type": "source",
              "style": {
                "top": 20,
                "right": -3
              }
            }
          }
        },
        {
          "id": "CONTACT_138504cb-bcb4-5477-a686-0da2e45c2b0c",
          "type": "contact",
          "position": {
            "x": 68,
            "y": 38
          },
          "height": 24,
          "width": 38,
          "measured": {
            "width": 38,
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
                  "x": 106,
                  "y": 50
                },
                "relPosition": {
                  "x": 38,
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
                  "x": 106,
                  "y": 50
                },
                "relPosition": {
                  "x": 38,
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
                "x": 106,
                "y": 50
              },
              "relPosition": {
                "x": 38,
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
            "numericId": "7124013",
            "variable": {
              "name": "CountPulse",
              "class": "local",
              "type": {
                "definition": "base-type",
                "value": "bool"
              },
              "location": "",
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
          "id": "VARIABLE_4e1a97e6-70c6-51cf-b57c-c6551bac1aad",
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
                  "x": 227,
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
                  "x": 227,
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
                "x": 227,
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
            "numericId": "1395101",
            "variable": {
              "name": "CountDown",
              "class": "local",
              "type": {
                "definition": "base-type",
                "value": "bool"
              },
              "location": "",
              "initialValue": null,
              "documentation": "",
              "debug": false
            },
            "executionOrder": 0,
            "variant": "input",
            "block": {
              "id": "BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad",
              "handleId": "CD",
              "variableType": {
                "name": "CD",
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
          "id": "VARIABLE_cd4ccccc-b186-542e-a489-af705dcd3a3c",
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
                  "x": 227,
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
                  "x": 227,
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
                "x": 227,
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
            "numericId": "9734562",
            "variable": {
              "name": "ResetCounter",
              "class": "local",
              "type": {
                "definition": "base-type",
                "value": "bool"
              },
              "location": "",
              "initialValue": null,
              "documentation": "",
              "debug": false
            },
            "executionOrder": 0,
            "variant": "input",
            "block": {
              "id": "BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad",
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
            "deletable": false
          }
        },
        {
          "id": "VARIABLE_147317c5-c8fd-59ab-b378-3889cbf4a517",
          "type": "variable",
          "position": {
            "x": 147,
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
                  "x": 227,
                  "y": 170
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
                  "x": 227,
                  "y": 170
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
                "x": 227,
                "y": 170
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
            "numericId": "6411568",
            "variable": {
              "name": "3",
              "class": "local",
              "type": {
                "definition": "base-type",
                "value": "dint"
              },
              "location": "",
              "initialValue": null,
              "documentation": "",
              "debug": false
            },
            "executionOrder": 0,
            "variant": "input",
            "block": {
              "id": "BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad",
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
          "id": "VARIABLE_267016a6-7f62-53a7-9d1c-51273519de49",
          "type": "variable",
          "position": {
            "x": 147,
            "y": 194
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
                  "x": 227,
                  "y": 210
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
                  "x": 227,
                  "y": 210
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
                "x": 227,
                "y": 210
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
            "numericId": "7493949",
            "variable": {
              "name": "2147483647",
              "class": "local",
              "type": {
                "definition": "base-type",
                "value": "dint"
              },
              "location": "",
              "initialValue": null,
              "documentation": "",
              "debug": false
            },
            "executionOrder": 0,
            "variant": "input",
            "block": {
              "id": "BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad",
              "handleId": "INITIAL_ACC",
              "variableType": {
                "name": "INITIAL_ACC",
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
          "id": "VARIABLE_e5af484c-5961-5f4f-8d77-d32bef9d6709",
          "type": "variable",
          "position": {
            "x": 147,
            "y": 234
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
                  "x": 227,
                  "y": 250
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
                  "x": 227,
                  "y": 250
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
                "x": 227,
                "y": 250
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
            "numericId": "3167879",
            "variable": {
              "name": "FALSE",
              "class": "local",
              "type": {
                "definition": "base-type",
                "value": "bool"
              },
              "location": "",
              "initialValue": null,
              "documentation": "",
              "debug": false
            },
            "executionOrder": 0,
            "variant": "input",
            "block": {
              "id": "BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad",
              "handleId": "INITIAL_DN",
              "variableType": {
                "name": "INITIAL_DN",
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
          "id": "VARIABLE_ff9e930b-03c9-5727-b3c0-cf2e60c57369",
          "type": "variable",
          "position": {
            "x": 147,
            "y": 274
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
                  "x": 227,
                  "y": 290
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
                  "x": 227,
                  "y": 290
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
                "x": 227,
                "y": 290
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
            "numericId": "4359483",
            "variable": {
              "name": "FALSE",
              "class": "local",
              "type": {
                "definition": "base-type",
                "value": "bool"
              },
              "location": "",
              "initialValue": null,
              "documentation": "",
              "debug": false
            },
            "executionOrder": 0,
            "variant": "input",
            "block": {
              "id": "BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad",
              "handleId": "INITIAL_OV",
              "variableType": {
                "name": "INITIAL_OV",
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
          "id": "VARIABLE_37e8d26b-f239-5da1-b6dd-7c8e7f469d79",
          "type": "variable",
          "position": {
            "x": 147,
            "y": 314
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
                  "x": 227,
                  "y": 330
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
                  "x": 227,
                  "y": 330
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
                "x": 227,
                "y": 330
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
            "numericId": "1947560",
            "variable": {
              "name": "FALSE",
              "class": "local",
              "type": {
                "definition": "base-type",
                "value": "bool"
              },
              "location": "",
              "initialValue": null,
              "documentation": "",
              "debug": false
            },
            "executionOrder": 0,
            "variant": "input",
            "block": {
              "id": "BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad",
              "handleId": "INITIAL_UN",
              "variableType": {
                "name": "INITIAL_UN",
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
          "id": "VARIABLE_5d51c007-5048-5dc1-b6cb-453b2471f9e4",
          "type": "variable",
          "position": {
            "x": 147,
            "y": 354
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
                  "x": 227,
                  "y": 370
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
                  "x": 227,
                  "y": 370
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
                "x": 227,
                "y": 370
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
            "numericId": "6896795",
            "variable": {
              "name": "TRUE",
              "class": "local",
              "type": {
                "definition": "base-type",
                "value": "bool"
              },
              "location": "",
              "initialValue": null,
              "documentation": "",
              "debug": false
            },
            "executionOrder": 0,
            "variant": "input",
            "block": {
              "id": "BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad",
              "handleId": "UP_FIRST",
              "variableType": {
                "name": "UP_FIRST",
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
          "id": "BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad",
          "type": "block",
          "position": {
            "x": 257,
            "y": 14
          },
          "height": 380,
          "width": 200,
          "measured": {
            "width": 200,
            "height": 380
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
                "id": "CD",
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
                "id": "RESET",
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
                  "x": 257,
                  "y": 170
                },
                "relPosition": {
                  "x": 0,
                  "y": 156
                },
                "id": "PV",
                "position": "left",
                "type": "target",
                "isConnectable": false,
                "style": {
                  "top": 156,
                  "left": 0
                }
              },
              {
                "glbPosition": {
                  "x": 257,
                  "y": 210
                },
                "relPosition": {
                  "x": 0,
                  "y": 196
                },
                "id": "INITIAL_ACC",
                "position": "left",
                "type": "target",
                "isConnectable": false,
                "style": {
                  "top": 196,
                  "left": 0
                }
              },
              {
                "glbPosition": {
                  "x": 257,
                  "y": 250
                },
                "relPosition": {
                  "x": 0,
                  "y": 236
                },
                "id": "INITIAL_DN",
                "position": "left",
                "type": "target",
                "isConnectable": false,
                "style": {
                  "top": 236,
                  "left": 0
                }
              },
              {
                "glbPosition": {
                  "x": 257,
                  "y": 290
                },
                "relPosition": {
                  "x": 0,
                  "y": 276
                },
                "id": "INITIAL_OV",
                "position": "left",
                "type": "target",
                "isConnectable": false,
                "style": {
                  "top": 276,
                  "left": 0
                }
              },
              {
                "glbPosition": {
                  "x": 257,
                  "y": 330
                },
                "relPosition": {
                  "x": 0,
                  "y": 316
                },
                "id": "INITIAL_UN",
                "position": "left",
                "type": "target",
                "isConnectable": false,
                "style": {
                  "top": 316,
                  "left": 0
                }
              },
              {
                "glbPosition": {
                  "x": 257,
                  "y": 370
                },
                "relPosition": {
                  "x": 0,
                  "y": 356
                },
                "id": "UP_FIRST",
                "position": "left",
                "type": "target",
                "isConnectable": false,
                "style": {
                  "top": 356,
                  "left": 0
                }
              },
              {
                "glbPosition": {
                  "x": 457,
                  "y": 50
                },
                "relPosition": {
                  "x": 200,
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
                  "x": 457,
                  "y": 90
                },
                "relPosition": {
                  "x": 200,
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
              },
              {
                "glbPosition": {
                  "x": 457,
                  "y": 130
                },
                "relPosition": {
                  "x": 200,
                  "y": 116
                },
                "id": "CUEnabled",
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
                  "x": 457,
                  "y": 170
                },
                "relPosition": {
                  "x": 200,
                  "y": 156
                },
                "id": "CDEnabled",
                "position": "right",
                "type": "source",
                "isConnectable": false,
                "style": {
                  "top": 156,
                  "right": 0
                }
              },
              {
                "glbPosition": {
                  "x": 457,
                  "y": 210
                },
                "relPosition": {
                  "x": 200,
                  "y": 196
                },
                "id": "OV",
                "position": "right",
                "type": "source",
                "isConnectable": false,
                "style": {
                  "top": 196,
                  "right": 0
                }
              },
              {
                "glbPosition": {
                  "x": 457,
                  "y": 250
                },
                "relPosition": {
                  "x": 200,
                  "y": 236
                },
                "id": "UN",
                "position": "right",
                "type": "source",
                "isConnectable": false,
                "style": {
                  "top": 236,
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
                "id": "CD",
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
                "id": "RESET",
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
                  "x": 257,
                  "y": 170
                },
                "relPosition": {
                  "x": 0,
                  "y": 156
                },
                "id": "PV",
                "position": "left",
                "type": "target",
                "isConnectable": false,
                "style": {
                  "top": 156,
                  "left": 0
                }
              },
              {
                "glbPosition": {
                  "x": 257,
                  "y": 210
                },
                "relPosition": {
                  "x": 0,
                  "y": 196
                },
                "id": "INITIAL_ACC",
                "position": "left",
                "type": "target",
                "isConnectable": false,
                "style": {
                  "top": 196,
                  "left": 0
                }
              },
              {
                "glbPosition": {
                  "x": 257,
                  "y": 250
                },
                "relPosition": {
                  "x": 0,
                  "y": 236
                },
                "id": "INITIAL_DN",
                "position": "left",
                "type": "target",
                "isConnectable": false,
                "style": {
                  "top": 236,
                  "left": 0
                }
              },
              {
                "glbPosition": {
                  "x": 257,
                  "y": 290
                },
                "relPosition": {
                  "x": 0,
                  "y": 276
                },
                "id": "INITIAL_OV",
                "position": "left",
                "type": "target",
                "isConnectable": false,
                "style": {
                  "top": 276,
                  "left": 0
                }
              },
              {
                "glbPosition": {
                  "x": 257,
                  "y": 330
                },
                "relPosition": {
                  "x": 0,
                  "y": 316
                },
                "id": "INITIAL_UN",
                "position": "left",
                "type": "target",
                "isConnectable": false,
                "style": {
                  "top": 316,
                  "left": 0
                }
              },
              {
                "glbPosition": {
                  "x": 257,
                  "y": 370
                },
                "relPosition": {
                  "x": 0,
                  "y": 356
                },
                "id": "UP_FIRST",
                "position": "left",
                "type": "target",
                "isConnectable": false,
                "style": {
                  "top": 356,
                  "left": 0
                }
              }
            ],
            "outputHandles": [
              {
                "glbPosition": {
                  "x": 457,
                  "y": 50
                },
                "relPosition": {
                  "x": 200,
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
                  "x": 457,
                  "y": 90
                },
                "relPosition": {
                  "x": 200,
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
              },
              {
                "glbPosition": {
                  "x": 457,
                  "y": 130
                },
                "relPosition": {
                  "x": 200,
                  "y": 116
                },
                "id": "CUEnabled",
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
                  "x": 457,
                  "y": 170
                },
                "relPosition": {
                  "x": 200,
                  "y": 156
                },
                "id": "CDEnabled",
                "position": "right",
                "type": "source",
                "isConnectable": false,
                "style": {
                  "top": 156,
                  "right": 0
                }
              },
              {
                "glbPosition": {
                  "x": 457,
                  "y": 210
                },
                "relPosition": {
                  "x": 200,
                  "y": 196
                },
                "id": "OV",
                "position": "right",
                "type": "source",
                "isConnectable": false,
                "style": {
                  "top": 196,
                  "right": 0
                }
              },
              {
                "glbPosition": {
                  "x": 457,
                  "y": 250
                },
                "relPosition": {
                  "x": 200,
                  "y": 236
                },
                "id": "UN",
                "position": "right",
                "type": "source",
                "isConnectable": false,
                "style": {
                  "top": 236,
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
                "x": 457,
                "y": 50
              },
              "relPosition": {
                "x": 200,
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
            "numericId": "3346305",
            "variant": {
              "name": "TF_COUNTER",
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
                  "name": "CD",
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
                  "name": "PV",
                  "class": "input",
                  "type": {
                    "definition": "base-type",
                    "value": "DINT"
                  }
                },
                {
                  "name": "INITIAL_ACC",
                  "class": "input",
                  "type": {
                    "definition": "base-type",
                    "value": "DINT"
                  }
                },
                {
                  "name": "INITIAL_DN",
                  "class": "input",
                  "type": {
                    "definition": "base-type",
                    "value": "BOOL"
                  }
                },
                {
                  "name": "INITIAL_OV",
                  "class": "input",
                  "type": {
                    "definition": "base-type",
                    "value": "BOOL"
                  }
                },
                {
                  "name": "INITIAL_UN",
                  "class": "input",
                  "type": {
                    "definition": "base-type",
                    "value": "BOOL"
                  }
                },
                {
                  "name": "UP_FIRST",
                  "class": "input",
                  "type": {
                    "definition": "base-type",
                    "value": "BOOL"
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
                  "name": "CUEnabled",
                  "class": "output",
                  "type": {
                    "definition": "base-type",
                    "value": "BOOL"
                  }
                },
                {
                  "name": "CDEnabled",
                  "class": "output",
                  "type": {
                    "definition": "base-type",
                    "value": "BOOL"
                  }
                },
                {
                  "name": "OV",
                  "class": "output",
                  "type": {
                    "definition": "base-type",
                    "value": "BOOL"
                  }
                },
                {
                  "name": "UN",
                  "class": "output",
                  "type": {
                    "definition": "base-type",
                    "value": "BOOL"
                  }
                }
              ],
              "body": "IF NOT Initialized THEN\n    CV := INITIAL_ACC;\n    Q := INITIAL_DN;\n    OV := INITIAL_OV;\n    UN := INITIAL_UN;\n    WasCU := CU;\n    WasCD := CD;\n    Initialized := TRUE;\nEND_IF;\n\nCUEnabled := CU;\nCDEnabled := CD;\nUpEdge := CU AND NOT WasCU;\nDownEdge := CD AND NOT WasCD;\n\nIF RESET THEN\n    CV := 0;\n    Q := FALSE;\n    OV := FALSE;\n    UN := FALSE;\n    CUEnabled := FALSE;\n    CDEnabled := FALSE;\n    WasCU := FALSE;\n    WasCD := FALSE;\nELSE\n    IF UP_FIRST THEN\n        IF UpEdge THEN\n            IF CV = 2147483647 THEN\n                CV := -2147483647 - 1;\n                OV := TRUE;\n            ELSE\n                CV := CV + 1;\n            END_IF;\n        END_IF;\n        IF DownEdge THEN\n            IF CV = -2147483647 - 1 THEN\n                CV := 2147483647;\n                UN := TRUE;\n            ELSE\n                CV := CV - 1;\n            END_IF;\n        END_IF;\n    ELSE\n        IF DownEdge THEN\n            IF CV = -2147483647 - 1 THEN\n                CV := 2147483647;\n                UN := TRUE;\n            ELSE\n                CV := CV - 1;\n            END_IF;\n        END_IF;\n        IF UpEdge THEN\n            IF CV = 2147483647 THEN\n                CV := -2147483647 - 1;\n                OV := TRUE;\n            ELSE\n                CV := CV + 1;\n            END_IF;\n        END_IF;\n    END_IF;\n    IF UpEdge OR DownEdge THEN\n        Q := CV >= PV;\n    END_IF;\n    WasCU := CU;\n    WasCD := CD;\nEND_IF;",
              "documentation": "TwinForge shared Rockwell counter state"
            },
            "variable": {
              "name": "PartCounter",
              "type": {
                "definition": "derived",
                "value": "TF_COUNTER"
              },
              "class": "local",
              "location": "",
              "documentation": "",
              "debug": false
            },
            "executionOrder": 0,
            "executionControl": false,
            "lockExecutionControl": false,
            "connectedVariables": [
              {
                "handleId": "CD",
                "type": "input",
                "variable": {
                  "name": "CountDown",
                  "class": "local",
                  "type": {
                    "definition": "base-type",
                    "value": "BOOL"
                  },
                  "location": "",
                  "initialValue": null,
                  "documentation": "",
                  "debug": false
                }
              },
              {
                "handleId": "RESET",
                "type": "input",
                "variable": {
                  "name": "ResetCounter",
                  "class": "local",
                  "type": {
                    "definition": "base-type",
                    "value": "BOOL"
                  },
                  "location": "",
                  "initialValue": null,
                  "documentation": "",
                  "debug": false
                }
              },
              {
                "handleId": "PV",
                "type": "input",
                "variable": {
                  "name": "3",
                  "class": "local",
                  "type": {
                    "definition": "base-type",
                    "value": "DINT"
                  },
                  "location": "",
                  "initialValue": null,
                  "documentation": "",
                  "debug": false
                }
              },
              {
                "handleId": "INITIAL_ACC",
                "type": "input",
                "variable": {
                  "name": "2147483647",
                  "class": "local",
                  "type": {
                    "definition": "base-type",
                    "value": "DINT"
                  },
                  "location": "",
                  "initialValue": null,
                  "documentation": "",
                  "debug": false
                }
              },
              {
                "handleId": "INITIAL_DN",
                "type": "input",
                "variable": {
                  "name": "FALSE",
                  "class": "local",
                  "type": {
                    "definition": "base-type",
                    "value": "BOOL"
                  },
                  "location": "",
                  "initialValue": null,
                  "documentation": "",
                  "debug": false
                }
              },
              {
                "handleId": "INITIAL_OV",
                "type": "input",
                "variable": {
                  "name": "FALSE",
                  "class": "local",
                  "type": {
                    "definition": "base-type",
                    "value": "BOOL"
                  },
                  "location": "",
                  "initialValue": null,
                  "documentation": "",
                  "debug": false
                }
              },
              {
                "handleId": "INITIAL_UN",
                "type": "input",
                "variable": {
                  "name": "FALSE",
                  "class": "local",
                  "type": {
                    "definition": "base-type",
                    "value": "BOOL"
                  },
                  "location": "",
                  "initialValue": null,
                  "documentation": "",
                  "debug": false
                }
              },
              {
                "handleId": "UP_FIRST",
                "type": "input",
                "variable": {
                  "name": "TRUE",
                  "class": "local",
                  "type": {
                    "definition": "base-type",
                    "value": "BOOL"
                  },
                  "location": "",
                  "initialValue": null,
                  "documentation": "",
                  "debug": false
                }
              },
              {
                "handleId": "CV",
                "type": "output",
                "variable": {
                  "name": "PartCounter_ACC",
                  "class": "local",
                  "type": {
                    "definition": "base-type",
                    "value": "DINT"
                  },
                  "location": "",
                  "initialValue": null,
                  "documentation": "",
                  "debug": false
                }
              },
              {
                "handleId": "OV",
                "type": "output",
                "variable": {
                  "name": "PartCounter_OV",
                  "class": "local",
                  "type": {
                    "definition": "base-type",
                    "value": "BOOL"
                  },
                  "location": "",
                  "initialValue": null,
                  "documentation": "",
                  "debug": false
                }
              },
              {
                "handleId": "UN",
                "type": "output",
                "variable": {
                  "name": "PartCounter_UN",
                  "class": "local",
                  "type": {
                    "definition": "base-type",
                    "value": "BOOL"
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
            "deletable": true,
            "hasDivergence": false
          }
        },
        {
          "id": "VARIABLE_06f54b09-b3fa-589a-a8ab-e7a108b43161",
          "type": "variable",
          "position": {
            "x": 487,
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
                  "x": 487,
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
                  "x": 487,
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
                "x": 487,
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
            "numericId": "1386992",
            "variable": {
              "name": "PartCounter_ACC",
              "class": "local",
              "type": {
                "definition": "base-type",
                "value": "dint"
              },
              "location": "",
              "initialValue": null,
              "documentation": "",
              "debug": false
            },
            "executionOrder": 0,
            "variant": "output",
            "block": {
              "id": "BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad",
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
        },
        {
          "id": "VARIABLE_6ad0a3ce-4f8f-5ff7-a08e-29bfab0c0e3f",
          "type": "variable",
          "position": {
            "x": 487,
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
                  "x": 487,
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
                  "x": 487,
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
                "x": 487,
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
            "numericId": "7186975",
            "variable": {
              "name": "PartCounter_OV",
              "class": "local",
              "type": {
                "definition": "base-type",
                "value": "bool"
              },
              "location": "",
              "initialValue": null,
              "documentation": "",
              "debug": false
            },
            "executionOrder": 0,
            "variant": "output",
            "block": {
              "id": "BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad",
              "handleId": "OV",
              "variableType": {
                "name": "OV",
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
          "id": "VARIABLE_be1eadba-2950-504f-8704-743f0d9347a8",
          "type": "variable",
          "position": {
            "x": 487,
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
                  "x": 487,
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
                  "x": 487,
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
                "x": 487,
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
            "numericId": "9907327",
            "variable": {
              "name": "PartCounter_UN",
              "class": "local",
              "type": {
                "definition": "base-type",
                "value": "bool"
              },
              "location": "",
              "initialValue": null,
              "documentation": "",
              "debug": false
            },
            "executionOrder": 0,
            "variant": "output",
            "block": {
              "id": "BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad",
              "handleId": "UN",
              "variableType": {
                "name": "UN",
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
          "id": "COIL_fc977140-a4ad-53ee-bf83-b979e212a258",
          "type": "coil",
          "position": {
            "x": 622,
            "y": 38
          },
          "height": 24,
          "width": 38,
          "measured": {
            "width": 38,
            "height": 24
          },
          "draggable": false,
          "selectable": true,
          "data": {
            "handles": [
              {
                "glbPosition": {
                  "x": 622,
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
                  "x": 660,
                  "y": 50
                },
                "relPosition": {
                  "x": 38,
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
                  "x": 622,
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
                  "x": 660,
                  "y": 50
                },
                "relPosition": {
                  "x": 38,
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
                "x": 622,
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
                "x": 660,
                "y": 50
              },
              "relPosition": {
                "x": 38,
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
            "numericId": "6446761",
            "variable": {
              "name": "Done",
              "class": "local",
              "type": {
                "definition": "base-type",
                "value": "bool"
              },
              "location": "",
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
          "id": "right-rail-rung_main_b1629c6d-2e3a-5aa0-943f-0c250f8c3ff3",
          "type": "powerRail",
          "position": {
            "x": 760,
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
                  "x": 737,
                  "y": 50
                },
                "relPosition": {
                  "x": 3,
                  "y": 20
                },
                "id": "right-rail",
                "position": "left",
                "isConnectable": false,
                "type": "target",
                "style": {
                  "top": 20,
                  "left": -3
                }
              }
            ],
            "inputHandles": [
              {
                "glbPosition": {
                  "x": 737,
                  "y": 50
                },
                "relPosition": {
                  "x": 3,
                  "y": 20
                },
                "id": "right-rail",
                "position": "left",
                "isConnectable": false,
                "type": "target",
                "style": {
                  "top": 20,
                  "left": -3
                }
              }
            ],
            "outputHandles": [],
            "numericId": "6912528",
            "variant": "right",
            "variable": {
              "name": ""
            },
            "executionOrder": 0,
            "draggable": false,
            "selectable": false,
            "deletable": false,
            "hasDivergence": false,
            "inputConnector": {
              "glbPosition": {
                "x": 737,
                "y": 50
              },
              "relPosition": {
                "x": 3,
                "y": 20
              },
              "id": "right-rail",
              "position": "left",
              "isConnectable": false,
              "type": "target",
              "style": {
                "top": 20,
                "left": -3
              }
            }
          }
        }
      ],
      "edges": [
        {
          "id": "e_left-rail-rung_main_b1629c6d-2e3a-5aa0-943f-0c250f8c3ff3_CONTACT_138504cb-bcb4-5477-a686-0da2e45c2b0c__left-rail_input",
          "source": "left-rail-rung_main_b1629c6d-2e3a-5aa0-943f-0c250f8c3ff3",
          "sourceHandle": "left-rail",
          "target": "CONTACT_138504cb-bcb4-5477-a686-0da2e45c2b0c",
          "targetHandle": "input"
        },
        {
          "id": "e_CONTACT_138504cb-bcb4-5477-a686-0da2e45c2b0c_BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad__output_CU",
          "source": "CONTACT_138504cb-bcb4-5477-a686-0da2e45c2b0c",
          "sourceHandle": "output",
          "target": "BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad",
          "targetHandle": "CU"
        },
        {
          "id": "e_VARIABLE_4e1a97e6-70c6-51cf-b57c-c6551bac1aad_BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad__output_CD",
          "source": "VARIABLE_4e1a97e6-70c6-51cf-b57c-c6551bac1aad",
          "sourceHandle": "output",
          "target": "BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad",
          "targetHandle": "CD"
        },
        {
          "id": "e_VARIABLE_cd4ccccc-b186-542e-a489-af705dcd3a3c_BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad__output_RESET",
          "source": "VARIABLE_cd4ccccc-b186-542e-a489-af705dcd3a3c",
          "sourceHandle": "output",
          "target": "BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad",
          "targetHandle": "RESET"
        },
        {
          "id": "e_VARIABLE_147317c5-c8fd-59ab-b378-3889cbf4a517_BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad__output_PV",
          "source": "VARIABLE_147317c5-c8fd-59ab-b378-3889cbf4a517",
          "sourceHandle": "output",
          "target": "BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad",
          "targetHandle": "PV"
        },
        {
          "id": "e_VARIABLE_267016a6-7f62-53a7-9d1c-51273519de49_BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad__output_INITIAL_ACC",
          "source": "VARIABLE_267016a6-7f62-53a7-9d1c-51273519de49",
          "sourceHandle": "output",
          "target": "BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad",
          "targetHandle": "INITIAL_ACC"
        },
        {
          "id": "e_VARIABLE_e5af484c-5961-5f4f-8d77-d32bef9d6709_BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad__output_INITIAL_DN",
          "source": "VARIABLE_e5af484c-5961-5f4f-8d77-d32bef9d6709",
          "sourceHandle": "output",
          "target": "BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad",
          "targetHandle": "INITIAL_DN"
        },
        {
          "id": "e_VARIABLE_ff9e930b-03c9-5727-b3c0-cf2e60c57369_BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad__output_INITIAL_OV",
          "source": "VARIABLE_ff9e930b-03c9-5727-b3c0-cf2e60c57369",
          "sourceHandle": "output",
          "target": "BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad",
          "targetHandle": "INITIAL_OV"
        },
        {
          "id": "e_VARIABLE_37e8d26b-f239-5da1-b6dd-7c8e7f469d79_BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad__output_INITIAL_UN",
          "source": "VARIABLE_37e8d26b-f239-5da1-b6dd-7c8e7f469d79",
          "sourceHandle": "output",
          "target": "BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad",
          "targetHandle": "INITIAL_UN"
        },
        {
          "id": "e_VARIABLE_5d51c007-5048-5dc1-b6cb-453b2471f9e4_BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad__output_UP_FIRST",
          "source": "VARIABLE_5d51c007-5048-5dc1-b6cb-453b2471f9e4",
          "sourceHandle": "output",
          "target": "BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad",
          "targetHandle": "UP_FIRST"
        },
        {
          "id": "e_BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad_VARIABLE_06f54b09-b3fa-589a-a8ab-e7a108b43161__CV_input",
          "source": "BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad",
          "sourceHandle": "CV",
          "target": "VARIABLE_06f54b09-b3fa-589a-a8ab-e7a108b43161",
          "targetHandle": "input"
        },
        {
          "id": "e_BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad_VARIABLE_6ad0a3ce-4f8f-5ff7-a08e-29bfab0c0e3f__OV_input",
          "source": "BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad",
          "sourceHandle": "OV",
          "target": "VARIABLE_6ad0a3ce-4f8f-5ff7-a08e-29bfab0c0e3f",
          "targetHandle": "input"
        },
        {
          "id": "e_BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad_VARIABLE_be1eadba-2950-504f-8704-743f0d9347a8__UN_input",
          "source": "BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad",
          "sourceHandle": "UN",
          "target": "VARIABLE_be1eadba-2950-504f-8704-743f0d9347a8",
          "targetHandle": "input"
        },
        {
          "id": "e_BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad_COIL_fc977140-a4ad-53ee-bf83-b979e212a258__Q_input",
          "source": "BLOCK_44be8ed2-9d64-579a-8f94-451152d753ad",
          "sourceHandle": "Q",
          "target": "COIL_fc977140-a4ad-53ee-bf83-b979e212a258",
          "targetHandle": "input"
        },
        {
          "id": "e_COIL_fc977140-a4ad-53ee-bf83-b979e212a258_right-rail-rung_main_b1629c6d-2e3a-5aa0-943f-0c250f8c3ff3__output_right-rail",
          "source": "COIL_fc977140-a4ad-53ee-bf83-b979e212a258",
          "sourceHandle": "output",
          "target": "right-rail-rung_main_b1629c6d-2e3a-5aa0-943f-0c250f8c3ff3",
          "targetHandle": "right-rail"
        }
      ]
    }
  ]
}
END_PROGRAM
