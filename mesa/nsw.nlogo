extensions [csv]

globals [
  next-trail-id
  next-ship-id
  remaining-ships
  spawn-duration
  scrubber-penalty-sum
  scrubber-penalty-count
  port-policy
  num-scrubber-ships
  num-scrubber-trails
  total-scrubber-water
  total-docked-ships
  avg-port-popularity
]

patches-own [
  terrain-type
]

breed [ports port-agent]
breed [ships ship-agent]
breed [trails trail]
breed [terrains terrain]

ports-own [
  name
  port-capacity
  current-capacity
  docked-ships
  scrubber-policy
  revenue
  base-fees
  allow-scrubber?
]

ships-own [
  ship-type
  docked?
  docking-steps
  route
  current-target-index
  is-scrubber?
  penalty
  wait-time
  exiting?
  exit-target
]

trails-own [
  water-units
  lifespan
]

to setup
  clear-all
  reset-ticks

  ; Initialize global variables
  set next-trail-id 10000
  set next-ship-id 0
  set remaining-ships num-ships
  set spawn-duration 3
  set scrubber-penalty-sum 0
  set scrubber-penalty-count 0

  ; Setup terrain
  setup-terrain

  ; Create ports from CSV
  setup-ports-from-csv

  ; Now set next-ship-id to be after all ports
  set next-ship-id count ports

  ; Gradually spawn ships
  if ticks < spawn-duration and remaining-ships > 0 [
    let spawn-rate ceiling (remaining-ships / (spawn-duration - ticks))
    repeat min (list spawn-rate remaining-ships) [
      spawn-ship next-ship-id
      set next-ship-id next-ship-id + 1
      set remaining-ships remaining-ships - 1
    ]
  ]
end

to setup-terrain
  ask patches [
    let is-land? false

    ; UK and islands (simplified)
    if (pxcor >= 0 and pxcor <= 26 and pycor >= 0 and pycor <= 2) [ set is-land? true ]
    if (pxcor >= 0 and pxcor <= 20 and pycor >= 3 and pycor <= 5) [ set is-land? true ]
    ; Add other regions as needed...

    set terrain-type ifelse-value is-land? ["land"] ["water"]
    set pcolor ifelse-value is-land? [gray] [blue]
  ]
end

to setup-ports-from-csv
  ask ports [ die ]

  carefully [
    let port-data csv:from-file "filtered_ports_with_x_y.csv"
    let port-records but-first port-data

    foreach port-records [ current-record ->
      let port-name item 5 current-record
      let x-coord item 0 current-record
      let y-coord item 1 current-record
      let capacity item 17 current-record

      let x safe-read x-coord
      let y safe-read y-coord

      if (x != false and y != false) [
        let adjusted-y max-pycor - y

        create-ports 1 [
          set name port-name
          setxy x adjusted-y

          ifelse capacity = "M" [
            set port-capacity 5
          ] [
            ifelse capacity = "L" [
              set port-capacity 10
            ] [
              set port-capacity 3
            ]
          ]

          let scaling-factor num-ships / (length port-records)
          set port-capacity round (port-capacity * scaling-factor)

          set current-capacity 0
          set docked-ships []
          set revenue 0
          set base-fees [100 120 50 40 30 80 60 35 20]
          set scrubber-policy one-of ["allow" "ban" "tax" "subsidy"]
          set allow-scrubber? (scrubber-policy != "ban")
          update-port-color
          set shape "house"
          set size 2 + (port-capacity / 5)
        ]
      ]
    ]
  ] [
    user-message "Could not load port data file!"
  ]
end

to update-port-color  ; port procedure
  ifelse scrubber-policy = "ban" [
    set color black
  ] [
    ifelse scrubber-policy = "tax" [
      set color orange
    ] [
      ifelse scrubber-policy = "subsidy" [
        set color green
      ] [
        set color brown
      ]
    ]
  ]
end

to spawn-ship [ship-id]
  create-ships 1 [
    set who ship-id
    set ship-type one-of ["cargo" "tanker" "fishing" "other" "tug" "passenger" "hsc" "dredging" "search"]
    set docked? false
    set docking-steps 0
    set current-target-index 0
    set wait-time 0
    set exiting? false

    let base-prob 0.05
    if ship-type = "cargo" [ set base-prob 0.18 ]
    if ship-type = "tanker" [ set base-prob 0.13 ]

    let avg-penalty get-average-penalty
    let adjusted-prob base-prob / (1 + avg-penalty)
    set is-scrubber? (random-float 1 < adjusted-prob)
    set penalty 0

    let start-patch one-of patches with [
      terrain-type = "water" and pycor = min-pycor and pxcor <= 38
    ]
    if start-patch != nobody [ move-to start-patch ]

    set route weighted-random-sample ports [get-port-weight ?] 3
    set color get-ship-color
  ]
end

to-report get-port-weight [a-port]
  let weight 1
  if [name] of a-port = "rotterdam" [ set weight 8 ]
  if [name] of a-port = "antwerp" [ set weight 5 ]
  if [name] of a-port = "amsterdam" or [name] of a-port = "hamburg" [ set weight 2 ]

  let factor 1.0
  if ship-type = "fishing" [ set factor 0.8 ]
  if ship-type = "other" [ set factor 0.8 ]
  if ship-type = "tug" [ set factor 0.5 ]
  if ship-type = "passenger" [ set factor 1.2 ]
  if ship-type = "hsc" [ set factor 1.2 ]
  if ship-type = "dredging" [ set factor 0.6 ]
  if ship-type = "search" [ set factor 0.7 ]

  if [scrubber-policy] of a-port = "ban" and is-scrubber? [ set weight 0 ]
  if [scrubber-policy] of a-port = "tax" and is-scrubber? [ set weight * 0.5 ]
  if [scrubber-policy] of a-port = "subsidy" and not is-scrubber? [ set weight * 1.5 ]

  report weight * factor
end

to-report get-ship-color
  if is-scrubber? [ report red ]
  report item position ship-type ["cargo" "tanker" "fishing" "other" "tug" "passenger" "hsc" "dredging" "search"]
    [blue navy yellow gray orange pink purple brown green]
end

to-report weighted-random-sample [agents weights k]
  let result []
  let agents-copy (list agents)
  let weights-copy (list weights)

  repeat k [
    if empty? agents-copy [ report result ]
    let total sum weights-copy
    let r random-float total
    let upto 0

    foreach weights-copy [ current-weight ->
      set upto upto + current-weight
      if upto >= r [
        set result lput (first agents-copy) result
        set agents-copy but-first agents-copy
        set weights-copy but-first weights-copy
        stop
      ]
    ]
  ]
  report result
end

to go
  if ticks < spawn-duration and remaining-ships > 0 [
    let spawn-rate ceiling (remaining-ships / (spawn-duration - ticks))
    repeat min (list spawn-rate remaining-ships) [
      spawn-ship next-ship-id
      set next-ship-id next-ship-id + 1
      set remaining-ships remaining-ships - 1
    ]
  ]

  move-ships
  update-trails
  collect-data
  tick
end

to move-ships
  ask ships [
    if exiting? [
      if not is-defined? exit-target [
        set exit-target one-of patches with [
          terrain-type = "water" and pycor = min-pycor and pxcor <= 38
        ]
        if exit-target = nobody [ set exit-target patch 0 0 ]
      ]

      face exit-target
      let target-patch patch-ahead 1
      if can-move-to? target-patch [
        if is-scrubber? [ leave-trail ]
        move-to target-patch
      ]

      if distance exit-target < 1 [
        spawn-ship next-ship-id
        set next-ship-id next-ship-id + 1
        die
      ]
    ]
    else [
      if not empty? route and current-target-index < length route [
        let target-port item current-target-index route
        face target-port

        let target-patch patch-ahead 1
        if can-move-to? target-patch [
          if is-scrubber? [ leave-trail ]
          move-to target-patch
        ]

        if distance target-port < 1 [
          ask target-port [
            ifelse dock-ship myself [
              set docked? true
              set docking-steps 0
              set wait-time 0
            ] [
              if is-scrubber? and not allow-scrubber? [
                set penalty penalty + 1
                set scrubber-penalty-sum scrubber-penalty-sum + 1
                set scrubber-penalty-count scrubber-penalty-count + 1
                set current-target-index current-target-index + 1
              ]
            ]
          ]
        ]
      ]

      set wait-time wait-time + 1
      if wait-time >= ship-wait-time [ set exiting? true ]
    ]

    if docked? [
      set docking-steps docking-steps + 1
      if docking-steps >= 10 [
        ask one-of ports with [member? myself docked-ships] [
          undock-ship myself
        ]
        set docked? false
        set current-target-index current-target-index + 1
      ]
    ]
  ]
end

to leave-trail  ; ship procedure
  create-trails 1 [
    set who next-trail-id
    set next-trail-id next-trail-id + 1
    set water-units 10
    set lifespan 60
    set shape "circle"
    set color orange
    set size 0.5
    move-to myself
  ]
end

to can-move-to? [target-patch]
  report target-patch != nobody and
         [terrain-type] of target-patch = "water" and
         not any? ports-on target-patch
end

to update-trails
  ask trails [
    set lifespan lifespan - 1
    if lifespan <= 0 [ die ]
  ]
end

to collect-data
  set num-scrubber-ships count ships with [is-scrubber?]
  set num-scrubber-trails count trails
  set total-scrubber-water sum [water-units] of trails
  set total-docked-ships sum [length docked-ships] of ports
  set avg-port-popularity ifelse-value (count ports > 0)
    [total-docked-ships / count ports] [0]
end

to-report get-average-penalty
  if scrubber-penalty-count > 0 [
    report scrubber-penalty-sum / scrubber-penalty-count
  ]
  report 0
end

to-report safe-read [str]
  carefully [
    report read-from-string str
  ] [
    report false
  ]
end

to dock-ship [a-ship]  ; port procedure
  if [is-scrubber?] of a-ship and scrubber-policy = "ban" [ report false ]

  if current-capacity < port-capacity [
    let fee calculate-docking-fee a-ship
    set revenue revenue + fee
    set current-capacity current-capacity + 1
    set docked-ships lput a-ship docked-ships
    report true
  ]
  report false
end

to undock-ship [a-ship]  ; port procedure
  if member? a-ship docked-ships [
    set docked-ships remove a-ship docked-ships
    set current-capacity current-capacity - 1
  ]
end

to-report calculate-docking-fee [a-ship]  ; port procedure
  let base-fee 40
  if [ship-type] of a-ship = "cargo" [ set base-fee 100 ]
  if [ship-type] of a-ship = "tanker" [ set base-fee 120 ]
  if [ship-type] of a-ship = "fishing" [ set base-fee 50 ]
  if [ship-type] of a-ship = "other" [ set base-fee 40 ]
  if [ship-type] of a-ship = "tug" [ set base-fee 30 ]
  if [ship-type] of a-ship = "passenger" [ set base-fee 80 ]
  if [ship-type] of a-ship = "hsc" [ set base-fee 60 ]
  if [ship-type] of a-ship = "dredging" [ set base-fee 35 ]
  if [ship-type] of a-ship = "search" [ set base-fee 20 ]

  if scrubber-policy = "tax" and [is-scrubber?] of a-ship [ set base-fee base-fee * 1.5 ]
  if scrubber-policy = "subsidy" and not [is-scrubber?] of a-ship [ set base-fee base-fee * 0.8 ]

  let occupancy-ratio current-capacity / port-capacity
  let multiplier 1 + occupancy-ratio

  report base-fee * multiplier
end
@#$#@#$#@
GRAPHICS-WINDOW
505
13
1123
632
-1
-1
10.0
1
10
1
1
1
0
1
1
1
-30
30
-30
30
0
0
1
ticks
30.0

SLIDER
40
122
212
155
num-ships
num-ships
10
200
50.0
10
1
NIL
HORIZONTAL

SLIDER
256
125
428
158
ship-wait-time
ship-wait-time
10
200
100.0
10
1
NIL
HORIZONTAL

CHOOSER
36
232
174
277
port-policy
port-policy
"allow" "ban" "tax" "subsidy" "random"
0

BUTTON
81
381
147
414
setup
setup
NIL
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

BUTTON
187
381
250
414
go
to go\n  if ticks < spawn-duration and remaining-ships > 0 [\n    let spawn-rate ceiling (remaining-ships / (spawn-duration - ticks))\n    repeat min (list spawn-rate remaining-ships) [\n      spawn-ship next-ship-id\n      set next-ship-id next-ship-id + 1\n      set remaining-ships remaining-ships - 1\n    ]\n  ]\n  \n  move-ships\n  update-trails\n  collect-data\n  tick\nend
T
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

SWITCH
262
227
388
260
show-trail?
show-trail?
1
1
-1000

PLOT
33
464
233
614
plot 1
NIL
NIL
0.0
10.0
0.0
10.0
true
false
"" ""
PENS
"default" 1.0 0 -16777216 true "" "plot count ships"
"pen-1" 1.0 0 -7500403 true "" "\"Scrubber Ships\" set-pen-color red plot num-scrubber-ships"

PLOT
285
495
485
645
plot 2
NIL
NIL
0.0
10.0
0.0
10.0
true
false
"" ""
PENS
"default" 1.0 0 -16777216 true "" "plot total-docked-ships"
"pen-1" 1.0 0 -7500403 true "" "\"Avg Port Popularity\" set-pen-color green plot avg-port-popularity"

@#$#@#$#@
## WHAT IS IT?

(a general understanding of what the model is trying to show or explain)

## HOW IT WORKS

(what rules the agents use to create the overall behavior of the model)

## HOW TO USE IT

(how to use the model, including a description of each of the items in the Interface tab)

## THINGS TO NOTICE

(suggested things for the user to notice while running the model)

## THINGS TO TRY

(suggested things for the user to try to do (move sliders, switches, etc.) with the model)

## EXTENDING THE MODEL

(suggested things to add or change in the Code tab to make the model more complicated, detailed, accurate, etc.)

## NETLOGO FEATURES

(interesting or unusual features of NetLogo that the model uses, particularly in the Code tab; or where workarounds were needed for missing features)

## RELATED MODELS

(models in the NetLogo Models Library and elsewhere which are of related interest)

## CREDITS AND REFERENCES

(a reference to the model's URL on the web if it has one, as well as any other necessary credits, citations, and links)
@#$#@#$#@
default
true
0
Polygon -7500403 true true 150 5 40 250 150 205 260 250

airplane
true
0
Polygon -7500403 true true 150 0 135 15 120 60 120 105 15 165 15 195 120 180 135 240 105 270 120 285 150 270 180 285 210 270 165 240 180 180 285 195 285 165 180 105 180 60 165 15

arrow
true
0
Polygon -7500403 true true 150 0 0 150 105 150 105 293 195 293 195 150 300 150

box
false
0
Polygon -7500403 true true 150 285 285 225 285 75 150 135
Polygon -7500403 true true 150 135 15 75 150 15 285 75
Polygon -7500403 true true 15 75 15 225 150 285 150 135
Line -16777216 false 150 285 150 135
Line -16777216 false 150 135 15 75
Line -16777216 false 150 135 285 75

bug
true
0
Circle -7500403 true true 96 182 108
Circle -7500403 true true 110 127 80
Circle -7500403 true true 110 75 80
Line -7500403 true 150 100 80 30
Line -7500403 true 150 100 220 30

butterfly
true
0
Polygon -7500403 true true 150 165 209 199 225 225 225 255 195 270 165 255 150 240
Polygon -7500403 true true 150 165 89 198 75 225 75 255 105 270 135 255 150 240
Polygon -7500403 true true 139 148 100 105 55 90 25 90 10 105 10 135 25 180 40 195 85 194 139 163
Polygon -7500403 true true 162 150 200 105 245 90 275 90 290 105 290 135 275 180 260 195 215 195 162 165
Polygon -16777216 true false 150 255 135 225 120 150 135 120 150 105 165 120 180 150 165 225
Circle -16777216 true false 135 90 30
Line -16777216 false 150 105 195 60
Line -16777216 false 150 105 105 60

car
false
0
Polygon -7500403 true true 300 180 279 164 261 144 240 135 226 132 213 106 203 84 185 63 159 50 135 50 75 60 0 150 0 165 0 225 300 225 300 180
Circle -16777216 true false 180 180 90
Circle -16777216 true false 30 180 90
Polygon -16777216 true false 162 80 132 78 134 135 209 135 194 105 189 96 180 89
Circle -7500403 true true 47 195 58
Circle -7500403 true true 195 195 58

circle
false
0
Circle -7500403 true true 0 0 300

circle 2
false
0
Circle -7500403 true true 0 0 300
Circle -16777216 true false 30 30 240

cow
false
0
Polygon -7500403 true true 200 193 197 249 179 249 177 196 166 187 140 189 93 191 78 179 72 211 49 209 48 181 37 149 25 120 25 89 45 72 103 84 179 75 198 76 252 64 272 81 293 103 285 121 255 121 242 118 224 167
Polygon -7500403 true true 73 210 86 251 62 249 48 208
Polygon -7500403 true true 25 114 16 195 9 204 23 213 25 200 39 123

cylinder
false
0
Circle -7500403 true true 0 0 300

dot
false
0
Circle -7500403 true true 90 90 120

face happy
false
0
Circle -7500403 true true 8 8 285
Circle -16777216 true false 60 75 60
Circle -16777216 true false 180 75 60
Polygon -16777216 true false 150 255 90 239 62 213 47 191 67 179 90 203 109 218 150 225 192 218 210 203 227 181 251 194 236 217 212 240

face neutral
false
0
Circle -7500403 true true 8 7 285
Circle -16777216 true false 60 75 60
Circle -16777216 true false 180 75 60
Rectangle -16777216 true false 60 195 240 225

face sad
false
0
Circle -7500403 true true 8 8 285
Circle -16777216 true false 60 75 60
Circle -16777216 true false 180 75 60
Polygon -16777216 true false 150 168 90 184 62 210 47 232 67 244 90 220 109 205 150 198 192 205 210 220 227 242 251 229 236 206 212 183

fish
false
0
Polygon -1 true false 44 131 21 87 15 86 0 120 15 150 0 180 13 214 20 212 45 166
Polygon -1 true false 135 195 119 235 95 218 76 210 46 204 60 165
Polygon -1 true false 75 45 83 77 71 103 86 114 166 78 135 60
Polygon -7500403 true true 30 136 151 77 226 81 280 119 292 146 292 160 287 170 270 195 195 210 151 212 30 166
Circle -16777216 true false 215 106 30

flag
false
0
Rectangle -7500403 true true 60 15 75 300
Polygon -7500403 true true 90 150 270 90 90 30
Line -7500403 true 75 135 90 135
Line -7500403 true 75 45 90 45

flower
false
0
Polygon -10899396 true false 135 120 165 165 180 210 180 240 150 300 165 300 195 240 195 195 165 135
Circle -7500403 true true 85 132 38
Circle -7500403 true true 130 147 38
Circle -7500403 true true 192 85 38
Circle -7500403 true true 85 40 38
Circle -7500403 true true 177 40 38
Circle -7500403 true true 177 132 38
Circle -7500403 true true 70 85 38
Circle -7500403 true true 130 25 38
Circle -7500403 true true 96 51 108
Circle -16777216 true false 113 68 74
Polygon -10899396 true false 189 233 219 188 249 173 279 188 234 218
Polygon -10899396 true false 180 255 150 210 105 210 75 240 135 240

house
false
0
Rectangle -7500403 true true 45 120 255 285
Rectangle -16777216 true false 120 210 180 285
Polygon -7500403 true true 15 120 150 15 285 120
Line -16777216 false 30 120 270 120

leaf
false
0
Polygon -7500403 true true 150 210 135 195 120 210 60 210 30 195 60 180 60 165 15 135 30 120 15 105 40 104 45 90 60 90 90 105 105 120 120 120 105 60 120 60 135 30 150 15 165 30 180 60 195 60 180 120 195 120 210 105 240 90 255 90 263 104 285 105 270 120 285 135 240 165 240 180 270 195 240 210 180 210 165 195
Polygon -7500403 true true 135 195 135 240 120 255 105 255 105 285 135 285 165 240 165 195

line
true
0
Line -7500403 true 150 0 150 300

line half
true
0
Line -7500403 true 150 0 150 150

pentagon
false
0
Polygon -7500403 true true 150 15 15 120 60 285 240 285 285 120

person
false
0
Circle -7500403 true true 110 5 80
Polygon -7500403 true true 105 90 120 195 90 285 105 300 135 300 150 225 165 300 195 300 210 285 180 195 195 90
Rectangle -7500403 true true 127 79 172 94
Polygon -7500403 true true 195 90 240 150 225 180 165 105
Polygon -7500403 true true 105 90 60 150 75 180 135 105

plant
false
0
Rectangle -7500403 true true 135 90 165 300
Polygon -7500403 true true 135 255 90 210 45 195 75 255 135 285
Polygon -7500403 true true 165 255 210 210 255 195 225 255 165 285
Polygon -7500403 true true 135 180 90 135 45 120 75 180 135 210
Polygon -7500403 true true 165 180 165 210 225 180 255 120 210 135
Polygon -7500403 true true 135 105 90 60 45 45 75 105 135 135
Polygon -7500403 true true 165 105 165 135 225 105 255 45 210 60
Polygon -7500403 true true 135 90 120 45 150 15 180 45 165 90

sheep
false
15
Circle -1 true true 203 65 88
Circle -1 true true 70 65 162
Circle -1 true true 150 105 120
Polygon -7500403 true false 218 120 240 165 255 165 278 120
Circle -7500403 true false 214 72 67
Rectangle -1 true true 164 223 179 298
Polygon -1 true true 45 285 30 285 30 240 15 195 45 210
Circle -1 true true 3 83 150
Rectangle -1 true true 65 221 80 296
Polygon -1 true true 195 285 210 285 210 240 240 210 195 210
Polygon -7500403 true false 276 85 285 105 302 99 294 83
Polygon -7500403 true false 219 85 210 105 193 99 201 83

square
false
0
Rectangle -7500403 true true 30 30 270 270

square 2
false
0
Rectangle -7500403 true true 30 30 270 270
Rectangle -16777216 true false 60 60 240 240

star
false
0
Polygon -7500403 true true 151 1 185 108 298 108 207 175 242 282 151 216 59 282 94 175 3 108 116 108

target
false
0
Circle -7500403 true true 0 0 300
Circle -16777216 true false 30 30 240
Circle -7500403 true true 60 60 180
Circle -16777216 true false 90 90 120
Circle -7500403 true true 120 120 60

tree
false
0
Circle -7500403 true true 118 3 94
Rectangle -6459832 true false 120 195 180 300
Circle -7500403 true true 65 21 108
Circle -7500403 true true 116 41 127
Circle -7500403 true true 45 90 120
Circle -7500403 true true 104 74 152

triangle
false
0
Polygon -7500403 true true 150 30 15 255 285 255

triangle 2
false
0
Polygon -7500403 true true 150 30 15 255 285 255
Polygon -16777216 true false 151 99 225 223 75 224

truck
false
0
Rectangle -7500403 true true 4 45 195 187
Polygon -7500403 true true 296 193 296 150 259 134 244 104 208 104 207 194
Rectangle -1 true false 195 60 195 105
Polygon -16777216 true false 238 112 252 141 219 141 218 112
Circle -16777216 true false 234 174 42
Rectangle -7500403 true true 181 185 214 194
Circle -16777216 true false 144 174 42
Circle -16777216 true false 24 174 42
Circle -7500403 false true 24 174 42
Circle -7500403 false true 144 174 42
Circle -7500403 false true 234 174 42

turtle
true
0
Polygon -10899396 true false 215 204 240 233 246 254 228 266 215 252 193 210
Polygon -10899396 true false 195 90 225 75 245 75 260 89 269 108 261 124 240 105 225 105 210 105
Polygon -10899396 true false 105 90 75 75 55 75 40 89 31 108 39 124 60 105 75 105 90 105
Polygon -10899396 true false 132 85 134 64 107 51 108 17 150 2 192 18 192 52 169 65 172 87
Polygon -10899396 true false 85 204 60 233 54 254 72 266 85 252 107 210
Polygon -7500403 true true 119 75 179 75 209 101 224 135 220 225 175 261 128 261 81 224 74 135 88 99

wheel
false
0
Circle -7500403 true true 3 3 294
Circle -16777216 true false 30 30 240
Line -7500403 true 150 285 150 15
Line -7500403 true 15 150 285 150
Circle -7500403 true true 120 120 60
Line -7500403 true 216 40 79 269
Line -7500403 true 40 84 269 221
Line -7500403 true 40 216 269 79
Line -7500403 true 84 40 221 269

wolf
false
0
Polygon -16777216 true false 253 133 245 131 245 133
Polygon -7500403 true true 2 194 13 197 30 191 38 193 38 205 20 226 20 257 27 265 38 266 40 260 31 253 31 230 60 206 68 198 75 209 66 228 65 243 82 261 84 268 100 267 103 261 77 239 79 231 100 207 98 196 119 201 143 202 160 195 166 210 172 213 173 238 167 251 160 248 154 265 169 264 178 247 186 240 198 260 200 271 217 271 219 262 207 258 195 230 192 198 210 184 227 164 242 144 259 145 284 151 277 141 293 140 299 134 297 127 273 119 270 105
Polygon -7500403 true true -1 195 14 180 36 166 40 153 53 140 82 131 134 133 159 126 188 115 227 108 236 102 238 98 268 86 269 92 281 87 269 103 269 113

x
false
0
Polygon -7500403 true true 270 75 225 30 30 225 75 270
Polygon -7500403 true true 30 75 75 30 270 225 225 270
@#$#@#$#@
NetLogo 6.4.0
@#$#@#$#@
@#$#@#$#@
@#$#@#$#@
@#$#@#$#@
@#$#@#$#@
default
0.0
-0.2 0 0.0 1.0
0.0 1 1.0 0.0
0.2 0 0.0 1.0
link direction
true
0
Line -7500403 true 150 150 90 180
Line -7500403 true 150 150 210 180
@#$#@#$#@
0
@#$#@#$#@
