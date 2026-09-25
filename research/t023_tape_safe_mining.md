# T023 tape-safe opportunity mining

Replays: 307; parent PASS unit-observations: 127469.

| op | PASS states | episodes | rate / 1k PASS |
|---|---:|---:|---:|
| COLLECT_FERTILIZER | 24290 | 307 | 190.56 |
| CARE | 24088 | 307 | 188.97 |
| FEED | 19193 | 307 | 150.57 |
| HARVEST_PLANT | 14783 | 307 | 115.97 |
| HARVEST_ANIMAL | 9865 | 307 | 77.39 |
| WATER | 6944 | 307 | 54.48 |
| FERTILIZE | 1722 | 307 | 13.51 |

## Sample states

### COLLECT_FERTILIZER
```json
[
  {
    "episode": 112612762,
    "step": null,
    "day": 1,
    "unit": 0,
    "tile": {
      "animal": "COW",
      "cared_today": false,
      "consecutive_unfed": 1,
      "fed_today": false,
      "fertilizer_available": true,
      "kind": "PASTURE",
      "pending_care_bonus": 0,
      "placed_day": 0,
      "yield_units": 0
    },
    "inv": {}
  },
  {
    "episode": 112612762,
    "step": null,
    "day": 2,
    "unit": 0,
    "tile": {
      "animal": "COW",
      "cared_today": false,
      "consecutive_unfed": 0,
      "fed_today": false,
      "fertilizer_available": true,
      "kind": "PASTURE",
      "pending_care_bonus": 1,
      "placed_day": 0,
      "yield_units": 0
    },
    "inv": {}
  },
  {
    "episode": 112612762,
    "step": null,
    "day": 3,
    "unit": 0,
    "tile": {
      "animal": "COW",
      "cared_today": false,
      "consecutive_unfed": 0,
      "fed_today": false,
      "fertilizer_available": true,
      "kind": "PASTURE",
      "pending_care_bonus": 2,
      "placed_day": 0,
      "yield_units": 0
    },
    "inv": {}
  },
  {
    "episode": 112612762,
    "step": null,
    "day": 4,
    "unit": 0,
    "tile": {
      "animal": "COW",
      "cared_today": false,
      "consecutive_unfed": 1,
      "fed_today": false,
      "fertilizer_available": true,
      "kind": "PASTURE",
      "pending_care_bonus": 2,
      "placed_day": 0,
      "yield_units": 0
    },
    "inv": {}
  },
  {
    "episode": 112612762,
    "step": null,
    "day": 5,
    "unit": 0,
    "tile": {
      "animal": "COW",
      "cared_today": false,
      "consecutive_unfed": 0,
      "fed_today": false,
      "fertilizer_available": true,
      "kind": "PASTURE",
      "pending_care_bonus": 3,
      "placed_day": 0,
      "yield_units": 0
    },
    "inv": {}
  }
]
```

### CARE
```json
[
  {
    "episode": 112612762,
    "step": null,
    "day": 1,
    "unit": 0,
    "tile": {
      "animal": "COW",
      "cared_today": false,
      "consecutive_unfed": 1,
      "fed_today": false,
      "fertilizer_available": true,
      "kind": "PASTURE",
      "pending_care_bonus": 0,
      "placed_day": 0,
      "yield_units": 0
    },
    "inv": {}
  },
  {
    "episode": 112612762,
    "step": null,
    "day": 2,
    "unit": 0,
    "tile": {
      "animal": "COW",
      "cared_today": false,
      "consecutive_unfed": 0,
      "fed_today": false,
      "fertilizer_available": true,
      "kind": "PASTURE",
      "pending_care_bonus": 1,
      "placed_day": 0,
      "yield_units": 0
    },
    "inv": {}
  },
  {
    "episode": 112612762,
    "step": null,
    "day": 3,
    "unit": 0,
    "tile": {
      "animal": "COW",
      "cared_today": false,
      "consecutive_unfed": 0,
      "fed_today": false,
      "fertilizer_available": true,
      "kind": "PASTURE",
      "pending_care_bonus": 2,
      "placed_day": 0,
      "yield_units": 0
    },
    "inv": {}
  },
  {
    "episode": 112612762,
    "step": null,
    "day": 4,
    "unit": 0,
    "tile": {
      "animal": "COW",
      "cared_today": false,
      "consecutive_unfed": 1,
      "fed_today": false,
      "fertilizer_available": true,
      "kind": "PASTURE",
      "pending_care_bonus": 2,
      "placed_day": 0,
      "yield_units": 0
    },
    "inv": {}
  },
  {
    "episode": 112612762,
    "step": null,
    "day": 5,
    "unit": 0,
    "tile": {
      "animal": "COW",
      "cared_today": false,
      "consecutive_unfed": 0,
      "fed_today": false,
      "fertilizer_available": true,
      "kind": "PASTURE",
      "pending_care_bonus": 3,
      "placed_day": 0,
      "yield_units": 0
    },
    "inv": {}
  }
]
```

### HARVEST_PLANT
```json
[
  {
    "episode": 112612762,
    "step": null,
    "day": 2,
    "unit": 1,
    "tile": {
      "consecutive_unwatered": 0,
      "crop": "WHEAT",
      "fertilized_until_day": -1,
      "kind": "PLANT",
      "max_lifespan_step": 120,
      "planted_day": 0,
      "watered_today": true,
      "yield_units": 2
    },
    "inv": {}
  },
  {
    "episode": 112612762,
    "step": null,
    "day": 2,
    "unit": 1,
    "tile": {
      "consecutive_unwatered": 0,
      "crop": "WHEAT",
      "fertilized_until_day": -1,
      "kind": "PLANT",
      "max_lifespan_step": 120,
      "planted_day": 0,
      "watered_today": true,
      "yield_units": 2
    },
    "inv": {}
  },
  {
    "episode": 112612762,
    "step": null,
    "day": 2,
    "unit": 1,
    "tile": {
      "consecutive_unwatered": 0,
      "crop": "WHEAT",
      "fertilized_until_day": -1,
      "kind": "PLANT",
      "max_lifespan_step": 120,
      "planted_day": 0,
      "watered_today": true,
      "yield_units": 2
    },
    "inv": {}
  },
  {
    "episode": 112612762,
    "step": null,
    "day": 2,
    "unit": 1,
    "tile": {
      "consecutive_unwatered": 0,
      "crop": "WHEAT",
      "fertilized_until_day": -1,
      "kind": "PLANT",
      "max_lifespan_step": 120,
      "planted_day": 0,
      "watered_today": true,
      "yield_units": 2
    },
    "inv": {}
  },
  {
    "episode": 112612762,
    "step": null,
    "day": 2,
    "unit": 1,
    "tile": {
      "consecutive_unwatered": 0,
      "crop": "WHEAT",
      "fertilized_until_day": -1,
      "kind": "PLANT",
      "max_lifespan_step": 120,
      "planted_day": 0,
      "watered_today": true,
      "yield_units": 2
    },
    "inv": {}
  }
]
```

### FEED
```json
[
  {
    "episode": 112612762,
    "step": null,
    "day": 3,
    "unit": 2,
    "tile": {
      "animal": "COW",
      "cared_today": true,
      "consecutive_unfed": 0,
      "fed_today": false,
      "fertilizer_available": false,
      "kind": "PASTURE",
      "pending_care_bonus": 2,
      "placed_day": 0,
      "yield_units": 0
    },
    "inv": {
      "WHEAT": 2
    }
  },
  {
    "episode": 112612762,
    "step": null,
    "day": 11,
    "unit": 1,
    "tile": {
      "animal": "SHEEP",
      "cared_today": false,
      "consecutive_unfed": 0,
      "fed_today": false,
      "fertilizer_available": true,
      "kind": "PASTURE",
      "pending_care_bonus": 1,
      "placed_day": 10,
      "yield_units": 0
    },
    "inv": {
      "FERTILIZER": 1,
      "WHEAT": 1
    }
  },
  {
    "episode": 112612762,
    "step": null,
    "day": 11,
    "unit": 1,
    "tile": {
      "animal": "SHEEP",
      "cared_today": false,
      "consecutive_unfed": 0,
      "fed_today": false,
      "fertilizer_available": true,
      "kind": "PASTURE",
      "pending_care_bonus": 1,
      "placed_day": 10,
      "yield_units": 0
    },
    "inv": {
      "FERTILIZER": 1,
      "WHEAT": 1
    }
  },
  {
    "episode": 112612762,
    "step": null,
    "day": 14,
    "unit": 4,
    "tile": {
      "animal": "SHEEP",
      "cared_today": false,
      "consecutive_unfed": 0,
      "fed_today": false,
      "fertilizer_available": true,
      "kind": "PASTURE",
      "pending_care_bonus": 3,
      "placed_day": 0,
      "yield_units": 0
    },
    "inv": {
      "WHEAT": 2
    }
  },
  {
    "episode": 112612762,
    "step": null,
    "day": 14,
    "unit": 8,
    "tile": {
      "animal": "COW",
      "cared_today": false,
      "consecutive_unfed": 0,
      "fed_today": false,
      "fertilizer_available": true,
      "kind": "PASTURE",
      "pending_care_bonus": 1,
      "placed_day": 2,
      "yield_units": 3
    },
    "inv": {
      "WHEAT": 2
    }
  }
]
```

### FERTILIZE
```json
[
  {
    "episode": 112612762,
    "step": null,
    "day": 5,
    "unit": 2,
    "tile": {
      "consecutive_unwatered": 0,
      "crop": "WHEAT",
      "fertilized_until_day": -1,
      "kind": "PLANT",
      "max_lifespan_step": 192,
      "planted_day": 3,
      "watered_today": true,
      "yield_units": 2
    },
    "inv": {
      "FERTILIZER": 1
    }
  },
  {
    "episode": 112612762,
    "step": null,
    "day": 8,
    "unit": 2,
    "tile": {
      "consecutive_unwatered": 0,
      "crop": "WHEAT",
      "fertilized_until_day": -1,
      "kind": "PLANT",
      "max_lifespan_step": 264,
      "planted_day": 6,
      "watered_today": true,
      "yield_units": 2
    },
    "inv": {
      "FERTILIZER": 1,
      "WHEAT": 2
    }
  },
  {
    "episode": 112612762,
    "step": null,
    "day": 18,
    "unit": 10,
    "tile": {
      "consecutive_unwatered": 1,
      "crop": "WHEAT",
      "fertilized_until_day": -1,
      "kind": "PLANT",
      "max_lifespan_step": 504,
      "planted_day": 16,
      "watered_today": true,
      "yield_units": 2
    },
    "inv": {
      "EGG": 4,
      "FERTILIZER": 2,
      "MILK": 6
    }
  },
  {
    "episode": 112609528,
    "step": null,
    "day": 5,
    "unit": 2,
    "tile": {
      "consecutive_unwatered": 0,
      "crop": "WHEAT",
      "fertilized_until_day": -1,
      "kind": "PLANT",
      "max_lifespan_step": 192,
      "planted_day": 3,
      "watered_today": true,
      "yield_units": 2
    },
    "inv": {
      "FERTILIZER": 1
    }
  },
  {
    "episode": 112609528,
    "step": null,
    "day": 8,
    "unit": 2,
    "tile": {
      "consecutive_unwatered": 0,
      "crop": "WHEAT",
      "fertilized_until_day": -1,
      "kind": "PLANT",
      "max_lifespan_step": 264,
      "planted_day": 6,
      "watered_today": true,
      "yield_units": 2
    },
    "inv": {
      "FERTILIZER": 1,
      "WHEAT": 2
    }
  }
]
```

### WATER
```json
[
  {
    "episode": 112612762,
    "step": null,
    "day": 7,
    "unit": 5,
    "tile": {
      "consecutive_unwatered": 1,
      "crop": "WHEAT",
      "fertilized_until_day": -1,
      "kind": "PLANT",
      "max_lifespan_step": 288,
      "planted_day": 7,
      "watered_today": false,
      "yield_units": 1
    },
    "inv": {
      "WHEAT": 1
    }
  },
  {
    "episode": 112612762,
    "step": null,
    "day": 14,
    "unit": 7,
    "tile": {
      "consecutive_unwatered": 1,
      "crop": "STRAWBERRY",
      "fertilized_until_day": -1,
      "kind": "PLANT",
      "max_lifespan_step": -1,
      "planted_day": 11,
      "watered_today": false,
      "yield_units": 0
    },
    "inv": {}
  },
  {
    "episode": 112612762,
    "step": null,
    "day": 14,
    "unit": 7,
    "tile": {
      "consecutive_unwatered": 1,
      "crop": "STRAWBERRY",
      "fertilized_until_day": -1,
      "kind": "PLANT",
      "max_lifespan_step": -1,
      "planted_day": 11,
      "watered_today": false,
      "yield_units": 0
    },
    "inv": {}
  },
  {
    "episode": 112612762,
    "step": null,
    "day": 14,
    "unit": 7,
    "tile": {
      "consecutive_unwatered": 1,
      "crop": "STRAWBERRY",
      "fertilized_until_day": -1,
      "kind": "PLANT",
      "max_lifespan_step": -1,
      "planted_day": 11,
      "watered_today": false,
      "yield_units": 0
    },
    "inv": {}
  },
  {
    "episode": 112612762,
    "step": null,
    "day": 14,
    "unit": 7,
    "tile": {
      "consecutive_unwatered": 1,
      "crop": "STRAWBERRY",
      "fertilized_until_day": -1,
      "kind": "PLANT",
      "max_lifespan_step": -1,
      "planted_day": 11,
      "watered_today": false,
      "yield_units": 0
    },
    "inv": {}
  }
]
```

### HARVEST_ANIMAL
```json
[
  {
    "episode": 112612762,
    "step": null,
    "day": 14,
    "unit": 0,
    "tile": {
      "animal": "COW",
      "cared_today": false,
      "consecutive_unfed": 0,
      "fed_today": false,
      "fertilizer_available": true,
      "kind": "PASTURE",
      "pending_care_bonus": 1,
      "placed_day": 0,
      "yield_units": 3
    },
    "inv": {}
  },
  {
    "episode": 112612762,
    "step": null,
    "day": 14,
    "unit": 8,
    "tile": {
      "animal": "COW",
      "cared_today": false,
      "consecutive_unfed": 0,
      "fed_today": false,
      "fertilizer_available": true,
      "kind": "PASTURE",
      "pending_care_bonus": 1,
      "placed_day": 2,
      "yield_units": 3
    },
    "inv": {
      "WHEAT": 2
    }
  },
  {
    "episode": 112612762,
    "step": null,
    "day": 17,
    "unit": 2,
    "tile": {
      "animal": "GOOSE",
      "cared_today": true,
      "consecutive_unfed": 0,
      "fed_today": true,
      "fertilizer_available": false,
      "kind": "COOP",
      "pending_care_bonus": 1,
      "placed_day": 6,
      "yield_units": 2
    },
    "inv": {}
  },
  {
    "episode": 112612762,
    "step": null,
    "day": 17,
    "unit": 2,
    "tile": {
      "animal": "GOOSE",
      "cared_today": true,
      "consecutive_unfed": 0,
      "fed_today": true,
      "fertilizer_available": false,
      "kind": "COOP",
      "pending_care_bonus": 1,
      "placed_day": 6,
      "yield_units": 2
    },
    "inv": {}
  },
  {
    "episode": 112612762,
    "step": null,
    "day": 17,
    "unit": 2,
    "tile": {
      "animal": "GOOSE",
      "cared_today": true,
      "consecutive_unfed": 0,
      "fed_today": true,
      "fertilizer_available": false,
      "kind": "COOP",
      "pending_care_bonus": 1,
      "placed_day": 6,
      "yield_units": 2
    },
    "inv": {}
  }
]
```

