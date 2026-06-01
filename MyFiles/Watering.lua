-- SMART IRRIGATION SYSTEM
send_message("info","Checking weather...")
-- CONFIG
local API_KEY = "22c46e8e2e78c0f15a2749ffc36c2a46"
local LAT = 33.9070
local LON = 73.3943
local SENSOR_PIN = 59
-- VARIABLES
local plant = variable("plant")
local soil_sensor = variable("soil_sensor")
-- MOVE FUNCTION
function go(x,y,z)
   move_absolute({
      x = x,
      y = y,
      z = z
   })
end
-- WEATHER CHECK
local url =
"https://api.openweathermap.org/data/2.5/weather?lat="
..LAT.."&lon="..LON..
"&appid="..API_KEY.."&units=metric"
local response = http({
   url = url,
   method = "GET"
})
if not response then
   send_message("error","Weather API failed")
   return
end
if response.status ~= 200 then
   send_message("error","API status failed")
   return
end
local body = response.body
local temp =
tonumber(string.match(body,'"temp":([%d%.%-]+)'))
local condition =
string.match(body,'"main":"([^"]+)"')
if not temp then
   send_message("error","Temperature parse failed")
   return
end
if not condition then
   send_message("error","Condition parse failed")
   return
end
send_message(
   "info",
   "Temp: "..tostring(temp).."C | "..condition
)
-- STOP CONDITIONS
if condition == "Rain"
or condition == "Drizzle" then
   send_message("warn","Rain detected")
   return
end
if temp < 15 then
   send_message("warn","Temperature too low")
   return
end
-- PICK SENSOR
send_message("success","Weather OK")
go(soil_sensor.x, soil_sensor.y, soil_sensor.z)
go(100, soil_sensor.y, soil_sensor.z)
-- MOVE TO PLANT
go(plant.x, plant.y, -450)
-- READ SOIL
send_message("info","Reading soil moisture")
read_pin(SENSOR_PIN,"analog")
wait(2000)
local moisture = 600
if pin_value then
   local value = pin_value(SENSOR_PIN)
   if value then
      moisture = value
   end
end
send_message(
   "info",
   "Moisture: "..tostring(moisture)
)
-- PLANT AGE
local age = plant.age
if not age then
   age = 30
end
send_message(
   "info",
   "Plant age: "..tostring(age)
)
-- RETURN SENSOR
go(plant.x, plant.y, -345)
go(100, soil_sensor.y, soil_sensor.z)
go(soil_sensor.x, soil_sensor.y, soil_sensor.z)
go(soil_sensor.x, soil_sensor.y, .345)
-- DECISION ENGINE
local duration = 0
if moisture > 700 then
   duration = 12000
elseif moisture > 500 then
   duration = 7000
elseif moisture > 350 then
   duration = 3000
else
   duration = 0
end
-- AGE FACTOR
if age < 10 then
   duration = duration * 1.5
elseif age > 30 then
   duration = duration * 0.7
end
duration = math.floor(duration)
-- FINAL DECISION
if duration <= 0 then
   send_message(
      "info",
      "Soil already wet → No watering"
   )
   return
end
send_message(
   "success",
   "Water duration: "..tostring(duration).." ms"
)