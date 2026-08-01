PROGRAM main
VAR
	Enable : bool AT %QX0.0;
	DelayTimer : TON;
	Output : bool AT %QX0.1;
	DelayTimer_ET : time;
	DelayTimer_ElapsedSeconds : dint AT %MD0;
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
        629,
        134
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
            "numericId": "7124013",
            "variable": {
              "name": "Enable",
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
          "id": "VARIABLE_e413e57e-353c-5bfe-a5bc-228c64d08d0d",
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
            "numericId": "5247399",
            "variable": {
              "name": "TIME#5000ms"
            },
            "executionOrder": 0,
            "variant": "input",
            "block": {
              "id": "BLOCK_3b3df7cf-d46f-5572-b6ed-cfa75dfaad2d",
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
            "deletable": false
          }
        },
        {
          "id": "BLOCK_3b3df7cf-d46f-5572-b6ed-cfa75dfaad2d",
          "type": "block",
          "position": {
            "x": 257,
            "y": 14
          },
          "height": 100,
          "width": 66,
          "measured": {
            "width": 66,
            "height": 100
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
                "id": "PT",
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
                  "x": 323,
                  "y": 50
                },
                "relPosition": {
                  "x": 66,
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
                  "x": 323,
                  "y": 90
                },
                "relPosition": {
                  "x": 66,
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
                "id": "PT",
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
                  "x": 323,
                  "y": 50
                },
                "relPosition": {
                  "x": 66,
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
                  "x": 323,
                  "y": 90
                },
                "relPosition": {
                  "x": 66,
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
                "x": 323,
                "y": 50
              },
              "relPosition": {
                "x": 66,
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
            "numericId": "2833007",
            "variant": {
              "name": "TON",
              "type": "function-block",
              "language": "st",
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
                }
              ],
              "documentation": "IEC on-delay timer"
            },
            "variable": {
              "name": "DelayTimer",
              "type": {
                "definition": "derived",
                "value": "TON"
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
                "handleId": "PT",
                "type": "input",
                "variable": {
                  "name": "TIME#5000ms"
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
          "id": "VARIABLE_f40a0278-bb2e-52b7-be98-d996fdf957cc",
          "type": "variable",
          "position": {
            "x": 353,
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
                  "x": 353,
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
                  "x": 353,
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
                "x": 353,
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
            "numericId": "5910305",
            "variable": {
              "name": "DelayTimer_ET",
              "class": "local",
              "type": {
                "definition": "base-type",
                "value": "time"
              },
              "location": "",
              "initialValue": null,
              "documentation": "",
              "debug": false,
              "id": "broken-VARIABLE_f40a0278-bb2e-52b7-be98-d996fdf957cc"
            },
            "executionOrder": 0,
            "variant": "output",
            "block": {
              "id": "BLOCK_3b3df7cf-d46f-5572-b6ed-cfa75dfaad2d",
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
            "deletable": false,
            "wrongVariable": true
          }
        },
        {
          "id": "COIL_fc977140-a4ad-53ee-bf83-b979e212a258",
          "type": "coil",
          "position": {
            "x": 488,
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
                  "x": 488,
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
                  "x": 516,
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
                  "x": 488,
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
                  "x": 516,
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
                "x": 488,
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
                "x": 516,
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
            "numericId": "6446761",
            "variable": {
              "name": "Output",
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
            "x": 626,
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
                  "x": 603,
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
                  "x": 603,
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
                "x": 603,
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
          "id": "e_CONTACT_138504cb-bcb4-5477-a686-0da2e45c2b0c_BLOCK_3b3df7cf-d46f-5572-b6ed-cfa75dfaad2d__output_IN",
          "source": "CONTACT_138504cb-bcb4-5477-a686-0da2e45c2b0c",
          "sourceHandle": "output",
          "target": "BLOCK_3b3df7cf-d46f-5572-b6ed-cfa75dfaad2d",
          "targetHandle": "IN"
        },
        {
          "id": "e_VARIABLE_e413e57e-353c-5bfe-a5bc-228c64d08d0d_BLOCK_3b3df7cf-d46f-5572-b6ed-cfa75dfaad2d__output_PT",
          "source": "VARIABLE_e413e57e-353c-5bfe-a5bc-228c64d08d0d",
          "sourceHandle": "output",
          "target": "BLOCK_3b3df7cf-d46f-5572-b6ed-cfa75dfaad2d",
          "targetHandle": "PT"
        },
        {
          "id": "e_BLOCK_3b3df7cf-d46f-5572-b6ed-cfa75dfaad2d_COIL_fc977140-a4ad-53ee-bf83-b979e212a258__Q_input",
          "source": "BLOCK_3b3df7cf-d46f-5572-b6ed-cfa75dfaad2d",
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
        },
        {
          "id": "e_BLOCK_3b3df7cf-d46f-5572-b6ed-cfa75dfaad2d_VARIABLE_f40a0278-bb2e-52b7-be98-d996fdf957cc__ET_input",
          "source": "BLOCK_3b3df7cf-d46f-5572-b6ed-cfa75dfaad2d",
          "sourceHandle": "ET",
          "target": "VARIABLE_f40a0278-bb2e-52b7-be98-d996fdf957cc",
          "targetHandle": "input"
        }
      ]
    },
    {
      "id": "rung_main_81167d85-747b-5783-aff0-f2c1c821f65a",
      "comment": "Expose DelayTimer.ET as whole elapsed seconds at %MD0.",
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
          "id": "left-rail-rung_main_81167d85-747b-5783-aff0-f2c1c821f65a",
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
            "numericId": "8103212",
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
          "id": "VARIABLE_290a36f9-fae0-5ebe-b592-791e5f5f31a8",
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
                  "x": 113,
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
                  "x": 113,
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
                "x": 113,
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
            "numericId": "1422858",
            "variable": {
              "name": "DelayTimer_ET",
              "class": "local",
              "type": {
                "definition": "base-type",
                "value": "time"
              },
              "location": "",
              "initialValue": null,
              "documentation": "",
              "debug": false,
              "id": "broken-VARIABLE_290a36f9-fae0-5ebe-b592-791e5f5f31a8"
            },
            "executionOrder": 0,
            "variant": "input",
            "block": {
              "id": "BLOCK_8155c7e9-e8dc-5ebc-81ed-f8d49003c541",
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
            "deletable": false,
            "wrongVariable": true
          }
        },
        {
          "id": "BLOCK_8155c7e9-e8dc-5ebc-81ed-f8d49003c541",
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
            "numericId": "8373892",
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
                "handleId": "IN",
                "type": "input",
                "variable": {
                  "name": "DelayTimer_ET",
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
              },
              {
                "handleId": "OUT",
                "type": "output",
                "variable": {
                  "name": "DelayTimer_ElapsedSeconds",
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
          "id": "VARIABLE_611889fe-adb1-5148-b4e0-7ebcbbc3b469",
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
            "numericId": "1642173",
            "variable": {
              "name": "DelayTimer_ElapsedSeconds",
              "class": "local",
              "type": {
                "definition": "base-type",
                "value": "dint"
              },
              "location": "%MD0",
              "initialValue": null,
              "documentation": "",
              "debug": false,
              "id": "broken-VARIABLE_611889fe-adb1-5148-b4e0-7ebcbbc3b469"
            },
            "executionOrder": 0,
            "variant": "output",
            "block": {
              "id": "BLOCK_8155c7e9-e8dc-5ebc-81ed-f8d49003c541",
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
            "deletable": false,
            "wrongVariable": true
          }
        },
        {
          "id": "right-rail-rung_main_81167d85-747b-5783-aff0-f2c1c821f65a",
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
                  "x": 524,
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
                  "x": 524,
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
            "numericId": "6645211",
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
                "x": 524,
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
          "id": "e_left-rail-rung_main_81167d85-747b-5783-aff0-f2c1c821f65a_BLOCK_8155c7e9-e8dc-5ebc-81ed-f8d49003c541__left-rail_EN",
          "source": "left-rail-rung_main_81167d85-747b-5783-aff0-f2c1c821f65a",
          "sourceHandle": "left-rail",
          "target": "BLOCK_8155c7e9-e8dc-5ebc-81ed-f8d49003c541",
          "targetHandle": "EN"
        },
        {
          "id": "e_BLOCK_8155c7e9-e8dc-5ebc-81ed-f8d49003c541_right-rail-rung_main_81167d85-747b-5783-aff0-f2c1c821f65a__ENO_right-rail",
          "source": "BLOCK_8155c7e9-e8dc-5ebc-81ed-f8d49003c541",
          "sourceHandle": "ENO",
          "target": "right-rail-rung_main_81167d85-747b-5783-aff0-f2c1c821f65a",
          "targetHandle": "right-rail"
        },
        {
          "id": "e_VARIABLE_290a36f9-fae0-5ebe-b592-791e5f5f31a8_BLOCK_8155c7e9-e8dc-5ebc-81ed-f8d49003c541__output_IN",
          "source": "VARIABLE_290a36f9-fae0-5ebe-b592-791e5f5f31a8",
          "sourceHandle": "output",
          "target": "BLOCK_8155c7e9-e8dc-5ebc-81ed-f8d49003c541",
          "targetHandle": "IN"
        },
        {
          "id": "e_BLOCK_8155c7e9-e8dc-5ebc-81ed-f8d49003c541_VARIABLE_611889fe-adb1-5148-b4e0-7ebcbbc3b469__OUT_input",
          "source": "BLOCK_8155c7e9-e8dc-5ebc-81ed-f8d49003c541",
          "sourceHandle": "OUT",
          "target": "VARIABLE_611889fe-adb1-5148-b4e0-7ebcbbc3b469",
          "targetHandle": "input"
        }
      ]
    }
  ]
}
END_PROGRAM