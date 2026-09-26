# Rules for dsm+mmpq (207 episodes, 170403 steps; test = 25% held-out episodes)

## BUY_LAND: positives 760; held-out acc 0.976, recall(pos) 0.98, precision 0.15
```
|--- price_MELON <= 267.50
|   |--- shed_MELON <= 17.50
|   |   |--- class: 0
|   |--- shed_MELON >  17.50
|   |   |--- inv_FERTILIZER <= 10138.50
|   |   |   |--- class: 1
|   |   |--- inv_FERTILIZER >  10138.50
|   |   |   |--- class: 0
|--- price_MELON >  267.50
|   |--- empty <= 2.50
|   |   |--- inv_WOOL <= 10027.50
|   |   |   |--- hour <= 14.50
|   |   |   |   |--- class: 1
|   |   |   |--- hour >  14.50
|   |   |   |   |--- class: 0
|   |   |--- inv_WOOL >  10027.50
|   |   |   |--- st_COOP <= 0.50
|   |   |   |   |--- class: 1
|   |   |   |--- st_COOP >  0.50
|   |   |   |   |--- class: 0
|   |--- empty >  2.50
|   |   |--- shed_MILK <= 5.50
|   |   |   |--- tile_WHEAT <= 26.50
|   |   |   |   |--- class: 0
|   |   |   |--- tile_WHEAT >  26.50
|   |   |   |   |--- class: 1
|   |   |--- shed_MILK >  5.50
|   |   |   |--- day <= 9.00
|   |   |   |   |--- class: 1
|   |   |   |--- day >  9.00
|   |   |   |   |--- class: 0
```

## HIRE: positives 12300; held-out acc 0.934, recall(pos) 0.83, precision 0.57
```
|--- hour <= 2.50
|   |--- hands <= 0.50
|   |   |--- money <= 0.50
|   |   |   |--- class: 3
|   |   |--- money >  0.50
|   |   |   |--- inv_TOMATO <= 9999.50
|   |   |   |   |--- class: 3
|   |   |   |--- inv_TOMATO >  9999.50
|   |   |   |   |--- class: 3
|   |--- hands >  0.50
|   |   |--- day <= 9.50
|   |   |   |--- ripe_MELON <= 37.50
|   |   |   |   |--- class: 1
|   |   |   |--- ripe_MELON >  37.50
|   |   |   |   |--- class: 2
|   |   |--- day >  9.50
|   |   |   |--- empty <= 5.50
|   |   |   |   |--- class: 2
|   |   |   |--- empty >  5.50
|   |   |   |   |--- class: 1
|--- hour >  2.50
|   |--- opp_money <= 0.50
|   |   |--- hour <= 3.50
|   |   |   |--- class: 1
|   |   |--- hour >  3.50
|   |   |   |--- n_shops <= 0.50
|   |   |   |   |--- class: 0
|   |   |   |--- n_shops >  0.50
|   |   |   |   |--- class: 0
|   |--- opp_money >  0.50
|   |   |--- shed_GOOSE <= 0.50
|   |   |   |--- ripe_WHEAT <= 0.50
|   |   |   |   |--- class: 0
|   |   |   |--- ripe_WHEAT >  0.50
|   |   |   |   |--- class: 0
|   |   |--- shed_GOOSE >  0.50
|   |   |   |--- shed_FERTILIZER <= 2.50
|   |   |   |   |--- class: 0
|   |   |   |--- shed_FERTILIZER >  2.50
|   |   |   |   |--- class: 0
```

## BUY_ANIMAL_GOOSE: positives 1783; held-out acc 0.942, recall(pos) 0.98, precision 0.14
```
|--- inv_MELON <= 9993.50
|   |--- empty <= 3.50
|   |   |--- empty <= 0.50
|   |   |   |--- ripe_MELON <= 23.50
|   |   |   |   |--- class: 0
|   |   |   |--- ripe_MELON >  23.50
|   |   |   |   |--- class: 0
|   |   |--- empty >  0.50
|   |   |   |--- hour <= 15.50
|   |   |   |   |--- class: 1
|   |   |   |--- hour >  15.50
|   |   |   |   |--- class: 0
|   |--- empty >  3.50
|   |   |--- hour <= 15.50
|   |   |   |--- hour <= 2.50
|   |   |   |   |--- class: 0
|   |   |   |--- hour >  2.50
|   |   |   |   |--- class: 1
|   |   |--- hour >  15.50
|   |   |   |--- inv_CARROT <= 9972.50
|   |   |   |   |--- class: 0
|   |   |   |--- inv_CARROT >  9972.50
|   |   |   |   |--- class: 0
|--- inv_MELON >  9993.50
|   |--- shed_MELON <= 11.50
|   |   |--- price_MELON <= 266.50
|   |   |   |--- hands <= 0.50
|   |   |   |   |--- class: 0
|   |   |   |--- hands >  0.50
|   |   |   |   |--- class: 0
|   |   |--- price_MELON >  266.50
|   |   |   |--- inv_CARROT <= 9967.00
|   |   |   |   |--- class: 0
|   |   |   |--- inv_CARROT >  9967.00
|   |   |   |   |--- class: 0
|   |--- shed_MELON >  11.50
|   |   |--- empty <= 5.50
|   |   |   |--- class: 0
|   |   |--- empty >  5.50
|   |   |   |--- inv_WOOL <= 9996.00
|   |   |   |   |--- class: 1
|   |   |   |--- inv_WOOL >  9996.00
|   |   |   |   |--- class: 0
```

## BUY_ANIMAL_COW: positives 2115; held-out acc 0.882, recall(pos) 0.98, precision 0.10
```
|--- day <= 9.50
|   |--- hour <= 14.50
|   |   |--- money <= 253.50
|   |   |   |--- shed_FERTILIZER <= 2.50
|   |   |   |   |--- class: 0
|   |   |   |--- shed_FERTILIZER >  2.50
|   |   |   |   |--- class: 1
|   |   |--- money >  253.50
|   |   |   |--- tile_STRAWBERRY <= 7.50
|   |   |   |   |--- class: 1
|   |   |   |--- tile_STRAWBERRY >  7.50
|   |   |   |   |--- class: 1
|   |--- hour >  14.50
|   |   |--- seed_MELON <= 3.50
|   |   |   |--- shed_COW <= 0.50
|   |   |   |   |--- class: 0
|   |   |   |--- shed_COW >  0.50
|   |   |   |   |--- class: 1
|   |   |--- seed_MELON >  3.50
|   |   |   |--- class: 1
|--- day >  9.50
|   |--- hires_today <= 1.50
|   |   |--- shed_WHEAT <= 44.50
|   |   |   |--- n_SHEEP <= 16.50
|   |   |   |   |--- class: 0
|   |   |   |--- n_SHEEP >  16.50
|   |   |   |   |--- class: 1
|   |   |--- shed_WHEAT >  44.50
|   |   |   |--- price_STRAWBERRY <= 148.50
|   |   |   |   |--- class: 0
|   |   |   |--- price_STRAWBERRY >  148.50
|   |   |   |   |--- class: 1
|   |--- hires_today >  1.50
|   |   |--- quads <= 3.50
|   |   |   |--- hands <= 6.50
|   |   |   |   |--- class: 0
|   |   |   |--- hands >  6.50
|   |   |   |   |--- class: 0
|   |   |--- quads >  3.50
|   |   |   |--- hires_today <= 10.50
|   |   |   |   |--- class: 1
|   |   |   |--- hires_today >  10.50
|   |   |   |   |--- class: 0
```

## BUY_ANIMAL_SHEEP: positives 1191; held-out acc 0.904, recall(pos) 0.94, precision 0.06
```
|--- money <= 4845.50
|   |--- hour <= 15.50
|   |   |--- empty <= 4.50
|   |   |   |--- n_SHEEP <= 3.50
|   |   |   |   |--- class: 0
|   |   |   |--- n_SHEEP >  3.50
|   |   |   |   |--- class: 1
|   |   |--- empty >  4.50
|   |   |   |--- shed_GOOSE <= 0.50
|   |   |   |   |--- class: 1
|   |   |   |--- shed_GOOSE >  0.50
|   |   |   |   |--- class: 0
|   |--- hour >  15.50
|   |   |--- n_SHEEP <= 5.50
|   |   |   |--- inv_MELON <= 9990.50
|   |   |   |   |--- class: 0
|   |   |   |--- inv_MELON >  9990.50
|   |   |   |   |--- class: 0
|   |   |--- n_SHEEP >  5.50
|   |   |   |--- inv_WOOL <= 9992.50
|   |   |   |   |--- class: 0
|   |   |   |--- inv_WOOL >  9992.50
|   |   |   |   |--- class: 1
|--- money >  4845.50
|   |--- hands <= 7.50
|   |   |--- day <= 21.50
|   |   |   |--- inv_TOMATO <= 9912.50
|   |   |   |   |--- class: 1
|   |   |   |--- inv_TOMATO >  9912.50
|   |   |   |   |--- class: 1
|   |   |--- day >  21.50
|   |   |   |--- n_SHEEP <= 0.50
|   |   |   |   |--- class: 0
|   |   |   |--- n_SHEEP >  0.50
|   |   |   |   |--- class: 0
|   |--- hands >  7.50
|   |   |--- shed_SHEEP <= 1.50
|   |   |   |--- opp_money <= 7198.00
|   |   |   |   |--- class: 0
|   |   |   |--- opp_money >  7198.00
|   |   |   |   |--- class: 0
|   |   |--- shed_SHEEP >  1.50
|   |   |   |--- class: 1
```

## SELL_EGG: positives 8162; held-out acc 0.835, recall(pos) 0.90, precision 0.21
```
|--- hour <= 17.50
|   |--- shed_EGG <= 9.50
|   |   |--- empty <= 43.50
|   |   |   |--- inv_CARROT <= 10073.50
|   |   |   |   |--- class: 0
|   |   |   |--- inv_CARROT >  10073.50
|   |   |   |   |--- class: 1
|   |   |--- empty >  43.50
|   |   |   |--- hour <= 15.50
|   |   |   |   |--- class: 0
|   |   |   |--- hour >  15.50
|   |   |   |   |--- class: 1
|   |--- shed_EGG >  9.50
|   |   |--- hour <= 13.50
|   |   |   |--- tile_TOMATO <= 0.50
|   |   |   |   |--- class: 0
|   |   |   |--- tile_TOMATO >  0.50
|   |   |   |   |--- class: 0
|   |   |--- hour >  13.50
|   |   |   |--- day <= 17.50
|   |   |   |   |--- class: 0
|   |   |   |--- day >  17.50
|   |   |   |   |--- class: 1
|--- hour >  17.50
|   |--- shed_EGG <= 0.50
|   |   |--- inv_EGG <= 10108.00
|   |   |   |--- price_MELON <= 77.00
|   |   |   |   |--- class: 0
|   |   |   |--- price_MELON >  77.00
|   |   |   |   |--- class: 0
|   |   |--- inv_EGG >  10108.00
|   |   |   |--- tile_STRAWBERRY <= 5.50
|   |   |   |   |--- class: 0
|   |   |   |--- tile_STRAWBERRY >  5.50
|   |   |   |   |--- class: 1
|   |--- shed_EGG >  0.50
|   |   |--- day <= 10.50
|   |   |   |--- opp_money <= 14473.50
|   |   |   |   |--- class: 0
|   |   |   |--- opp_money >  14473.50
|   |   |   |   |--- class: 0
|   |   |--- day >  10.50
|   |   |   |--- hour <= 21.50
|   |   |   |   |--- class: 1
|   |   |   |--- hour >  21.50
|   |   |   |   |--- class: 1
```

## SELL_WHEAT: positives 13755; held-out acc 0.799, recall(pos) 0.77, precision 0.25
```
|--- shed_WHEAT <= 36.50
|   |--- hour <= 2.50
|   |   |--- tile_STRAWBERRY <= 10.50
|   |   |   |--- shed_WHEAT <= 0.50
|   |   |   |   |--- class: 0
|   |   |   |--- shed_WHEAT >  0.50
|   |   |   |   |--- class: 1
|   |   |--- tile_STRAWBERRY >  10.50
|   |   |   |--- day <= 23.50
|   |   |   |   |--- class: 0
|   |   |   |--- day >  23.50
|   |   |   |   |--- class: 1
|   |--- hour >  2.50
|   |   |--- ripe_MELON <= 5.50
|   |   |   |--- hour <= 21.50
|   |   |   |   |--- class: 0
|   |   |   |--- hour >  21.50
|   |   |   |   |--- class: 1
|   |   |--- ripe_MELON >  5.50
|   |   |   |--- inv_MELON <= 9994.50
|   |   |   |   |--- class: 0
|   |   |   |--- inv_MELON >  9994.50
|   |   |   |   |--- class: 0
|--- shed_WHEAT >  36.50
|   |--- hour <= 21.50
|   |   |--- day <= 21.50
|   |   |   |--- empty <= 0.50
|   |   |   |   |--- class: 0
|   |   |   |--- empty >  0.50
|   |   |   |   |--- class: 1
|   |   |--- day >  21.50
|   |   |   |--- hires_today <= 9.50
|   |   |   |   |--- class: 1
|   |   |   |--- hires_today >  9.50
|   |   |   |   |--- class: 1
|   |--- hour >  21.50
|   |   |--- n_shops <= 3.50
|   |   |   |--- shed_WHEAT <= 48.50
|   |   |   |   |--- class: 0
|   |   |   |--- shed_WHEAT >  48.50
|   |   |   |   |--- class: 1
|   |   |--- n_shops >  3.50
|   |   |   |--- day <= 17.50
|   |   |   |   |--- class: 1
|   |   |   |--- day >  17.50
|   |   |   |   |--- class: 1
```

## BUY_PRODUCT_WHEAT: positives 6657; held-out acc 0.836, recall(pos) 0.91, precision 0.18
```
|--- money <= 5835.00
|   |--- hour <= 14.50
|   |   |--- price_WOOL <= 210.50
|   |   |   |--- hour <= 8.50
|   |   |   |   |--- class: 1
|   |   |   |--- hour >  8.50
|   |   |   |   |--- class: 1
|   |   |--- price_WOOL >  210.50
|   |   |   |--- inv_FERTILIZER <= 10043.50
|   |   |   |   |--- class: 0
|   |   |   |--- inv_FERTILIZER >  10043.50
|   |   |   |   |--- class: 1
|   |--- hour >  14.50
|   |   |--- shed_FERTILIZER <= 1.50
|   |   |   |--- n_SHEEP <= 3.50
|   |   |   |   |--- class: 0
|   |   |   |--- n_SHEEP >  3.50
|   |   |   |   |--- class: 0
|   |   |--- shed_FERTILIZER >  1.50
|   |   |   |--- hour <= 16.50
|   |   |   |   |--- class: 1
|   |   |   |--- hour >  16.50
|   |   |   |   |--- class: 0
|--- money >  5835.00
|   |--- hour <= 2.50
|   |   |--- shed_WHEAT <= 27.50
|   |   |   |--- day <= 25.50
|   |   |   |   |--- class: 1
|   |   |   |--- day >  25.50
|   |   |   |   |--- class: 0
|   |   |--- shed_WHEAT >  27.50
|   |   |   |--- day <= 11.50
|   |   |   |   |--- class: 1
|   |   |   |--- day >  11.50
|   |   |   |   |--- class: 0
|   |--- hour >  2.50
|   |   |--- shed_WHEAT <= 17.50
|   |   |   |--- shed_MELON <= 3.00
|   |   |   |   |--- class: 0
|   |   |   |--- shed_MELON >  3.00
|   |   |   |   |--- class: 1
|   |   |--- shed_WHEAT >  17.50
|   |   |   |--- money <= 8824.50
|   |   |   |   |--- class: 0
|   |   |   |--- money >  8824.50
|   |   |   |   |--- class: 0
```

## SELL_STRAWBERRY: positives 12922; held-out acc 0.658, recall(pos) 0.98, precision 0.18
```
|--- shed_STRAWBERRY <= 0.50
|   |--- class: 0
|--- shed_STRAWBERRY >  0.50
|   |--- n_shops <= 4.50
|   |   |--- shed_STRAWBERRY <= 4.50
|   |   |   |--- day <= 13.50
|   |   |   |   |--- class: 0
|   |   |   |--- day >  13.50
|   |   |   |   |--- class: 0
|   |   |--- shed_STRAWBERRY >  4.50
|   |   |   |--- hour <= 20.50
|   |   |   |   |--- class: 0
|   |   |   |--- hour >  20.50
|   |   |   |   |--- class: 1
|   |--- n_shops >  4.50
|   |   |--- hour <= 8.50
|   |   |   |--- hour <= 5.50
|   |   |   |   |--- class: 1
|   |   |   |--- hour >  5.50
|   |   |   |   |--- class: 0
|   |   |--- hour >  8.50
|   |   |   |--- hour <= 17.50
|   |   |   |   |--- class: 1
|   |   |   |--- hour >  17.50
|   |   |   |   |--- class: 1
```

## SELL_MILK: positives 11911; held-out acc 0.709, recall(pos) 0.81, precision 0.18
```
|--- shed_MILK <= 0.50
|   |--- class: 0
|--- shed_MILK >  0.50
|   |--- hour <= 1.50
|   |   |--- inv_MILK <= 10065.50
|   |   |   |--- hands <= 1.50
|   |   |   |   |--- class: 1
|   |   |   |--- hands >  1.50
|   |   |   |   |--- class: 1
|   |   |--- inv_MILK >  10065.50
|   |   |   |--- hires_today <= 6.50
|   |   |   |   |--- class: 0
|   |   |   |--- hires_today >  6.50
|   |   |   |   |--- class: 1
|   |--- hour >  1.50
|   |   |--- shed_MILK <= 5.50
|   |   |   |--- shed_FERTILIZER <= 1.50
|   |   |   |   |--- class: 1
|   |   |   |--- shed_FERTILIZER >  1.50
|   |   |   |   |--- class: 0
|   |   |--- shed_MILK >  5.50
|   |   |   |--- inv_MILK <= 10068.50
|   |   |   |   |--- class: 1
|   |   |   |--- inv_MILK >  10068.50
|   |   |   |   |--- class: 0
```

## SELL_WOOL: positives 10950; held-out acc 0.737, recall(pos) 0.96, precision 0.18
```
|--- shed_WOOL <= 0.50
|   |--- class: 0
|--- shed_WOOL >  0.50
|   |--- price_WOOL <= 21.00
|   |   |--- hands <= 9.50
|   |   |   |--- hands <= 7.50
|   |   |   |   |--- class: 0
|   |   |   |--- hands >  7.50
|   |   |   |   |--- class: 1
|   |   |--- hands >  9.50
|   |   |   |--- shed_STRAWBERRY <= 22.50
|   |   |   |   |--- class: 0
|   |   |   |--- shed_STRAWBERRY >  22.50
|   |   |   |   |--- class: 0
|   |--- price_WOOL >  21.00
|   |   |--- inv_STRAWBERRY <= 9929.50
|   |   |   |--- inv_WOOL <= 10051.50
|   |   |   |   |--- class: 1
|   |   |   |--- inv_WOOL >  10051.50
|   |   |   |   |--- class: 0
|   |   |--- inv_STRAWBERRY >  9929.50
|   |   |   |--- hour <= 6.50
|   |   |   |   |--- class: 1
|   |   |   |--- hour >  6.50
|   |   |   |   |--- class: 1
```

## SELL_MELON: positives 2501; held-out acc 0.975, recall(pos) 0.99, precision 0.36
```
|--- shed_MELON <= 2.50
|   |--- seed_TOMATO <= 0.50
|   |   |--- class: 0
|   |--- seed_TOMATO >  0.50
|   |   |--- class: 0
|--- shed_MELON >  2.50
|   |--- ripe_MELON <= 35.50
|   |   |--- hour <= 16.50
|   |   |   |--- shed_MELON <= 8.50
|   |   |   |   |--- class: 1
|   |   |   |--- shed_MELON >  8.50
|   |   |   |   |--- class: 1
|   |   |--- hour >  16.50
|   |   |   |--- shed_WHEAT <= 51.50
|   |   |   |   |--- class: 1
|   |   |   |--- shed_WHEAT >  51.50
|   |   |   |   |--- class: 0
|   |--- ripe_MELON >  35.50
|   |   |--- shed_FERTILIZER <= 0.50
|   |   |   |--- class: 0
|   |   |--- shed_FERTILIZER >  0.50
|   |   |   |--- class: 0
```

## BUY_SEED_WHEAT: positives 31753; held-out acc 0.787, recall(pos) 0.92, precision 0.46
```
|--- empty <= 0.50
|   |--- hour <= 10.50
|   |   |--- hour <= 9.50
|   |   |   |--- st_PASTURE <= 26.50
|   |   |   |   |--- class: 0
|   |   |   |--- st_PASTURE >  26.50
|   |   |   |   |--- class: 0
|   |   |--- hour >  9.50
|   |   |   |--- shed_WOOL <= 14.50
|   |   |   |   |--- class: 0
|   |   |   |--- shed_WOOL >  14.50
|   |   |   |   |--- class: 0
|   |--- hour >  10.50
|   |   |--- tile_WHEAT <= 20.50
|   |   |   |--- tile_MELON <= 3.50
|   |   |   |   |--- class: 0
|   |   |   |--- tile_MELON >  3.50
|   |   |   |   |--- class: 0
|   |   |--- tile_WHEAT >  20.50
|   |   |   |--- hour <= 20.50
|   |   |   |   |--- class: 0
|   |   |   |--- hour >  20.50
|   |   |   |   |--- class: 0
|--- empty >  0.50
|   |--- seed_WHEAT <= 0.50
|   |   |--- seed_MELON <= 2.50
|   |   |   |--- inv_MELON <= 9993.50
|   |   |   |   |--- class: 0
|   |   |   |--- inv_MELON >  9993.50
|   |   |   |   |--- class: 0
|   |   |--- seed_MELON >  2.50
|   |   |   |--- empty <= 5.50
|   |   |   |   |--- class: 0
|   |   |   |--- empty >  5.50
|   |   |   |   |--- class: 1
|   |--- seed_WHEAT >  0.50
|   |   |--- hour <= 5.50
|   |   |   |--- hour <= 4.50
|   |   |   |   |--- class: 0
|   |   |   |--- hour >  4.50
|   |   |   |   |--- class: 0
|   |   |--- hour >  5.50
|   |   |   |--- hour <= 20.50
|   |   |   |   |--- class: 1
|   |   |   |--- hour >  20.50
|   |   |   |   |--- class: 0
```

## BUY_SEED_STRAWBERRY: positives 6479; held-out acc 0.873, recall(pos) 0.94, precision 0.23
```
|--- price_MELON <= 261.00
|   |--- day <= 15.50
|   |   |--- hour <= 1.50
|   |   |   |--- n_shops <= 3.50
|   |   |   |   |--- class: 0
|   |   |   |--- n_shops >  3.50
|   |   |   |   |--- class: 1
|   |   |--- hour >  1.50
|   |   |   |--- seed_STRAWBERRY <= 1.50
|   |   |   |   |--- class: 0
|   |   |   |--- seed_STRAWBERRY >  1.50
|   |   |   |   |--- class: 1
|   |--- day >  15.50
|   |   |--- ripe_MELON <= 8.50
|   |   |   |--- empty <= 0.50
|   |   |   |   |--- class: 0
|   |   |   |--- empty >  0.50
|   |   |   |   |--- class: 0
|   |   |--- ripe_MELON >  8.50
|   |   |   |--- tile_WHEAT <= 27.50
|   |   |   |   |--- class: 0
|   |   |   |--- tile_WHEAT >  27.50
|   |   |   |   |--- class: 1
|--- price_MELON >  261.00
|   |--- empty <= 0.50
|   |   |--- hour <= 9.50
|   |   |   |--- hour <= 7.50
|   |   |   |   |--- class: 0
|   |   |   |--- hour >  7.50
|   |   |   |   |--- class: 0
|   |   |--- hour >  9.50
|   |   |   |--- hour <= 16.50
|   |   |   |   |--- class: 1
|   |   |   |--- hour >  16.50
|   |   |   |   |--- class: 0
|   |--- empty >  0.50
|   |   |--- day <= 6.50
|   |   |   |--- hour <= 20.50
|   |   |   |   |--- class: 1
|   |   |   |--- hour >  20.50
|   |   |   |   |--- class: 0
|   |   |--- day >  6.50
|   |   |   |--- seed_STRAWBERRY <= 0.50
|   |   |   |   |--- class: 0
|   |   |   |--- seed_STRAWBERRY >  0.50
|   |   |   |   |--- class: 1
```
