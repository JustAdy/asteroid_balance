#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>
#include <HX711.h>
#include "Joystick.h" // https://github.com/MHeironimus/ArduinoJoystickLibrary/tree/version-1.0

Adafruit_MPU6050 mpu;
HX711 hx;

// Set to true to test "Auto Send" mode or false to test "Manual Send" mode.
//const bool testAutoSendMode = true;
const bool testAutoSendMode = true;

void setup(void) {
  Serial.begin(115200);

  // Try to initialize!
  if (!mpu.begin()) {
    Serial.println("Failed to find MPU6050 chip");
    while (1) {
      delay(10);
    }
  }
  Serial.println("MPU6050 Found!");

  // set accelerometer range to +-8G
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);

  // set gyro range to +- 250 deg/s
  mpu.setGyroRange(MPU6050_RANGE_250_DEG);

  // set filter bandwidth to 21 Hz
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);

  if (testAutoSendMode)
  {
    Joystick.begin();
  }
  else
  {
    Joystick.begin(false);
  }

  hx.begin(4, 5, false, true);
  hx.set_rate_80SPS();

  hx.tare();

  Serial.println("Wait HX711 ready...");
  while(!hx.is_ready());

  delay(100);
}

void loop() {
  /* Get new sensor events with the readings */
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  a.acceleration.y = constrain(a.acceleration.y * 10, -30, 30);
  a.acceleration.y = map(a.acceleration.y, -30, 30, -127, 127);

  Joystick.setXAxis(a.acceleration.y);

  float weight = 0;
  if (hx.is_ready())
  {
    weight = hx.read();
    Serial.print("Weight: ");
    Serial.println(weight);
  }

  Serial.print(a.acceleration.y);
  Serial.println("");
  delay(50);
}