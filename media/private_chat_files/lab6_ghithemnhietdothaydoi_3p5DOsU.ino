#include <Wire.h>
#include <RTClib.h>
#include <SPI.h>
#include <SD.h>
// CS (Chip Select)	10	Chọn thiết bị SPI
// MOSI	11	Dữ liệu từ Arduino
// MISO	12	Dữ liệu đến Arduinojk
// SCK	13	Xung clock SPI
// VCC	5V hoặc 3.3V	Nguồn cấp
// GND	GND	Mass chung


// VCC	5V	Nguồn cấp
// GND	GND	Mass chung
// SDA	A4	Dữ liệu I2C
// SCL	A5	Clock I2C
#define LM35PIN A0  // Chân kết nối cảm biến LM35

RTC_DS1307 rtc;
const int chipSelect = 10;
float previousTemp = -999.0; // Biến lưu trữ nhiệt độ trước đó, giá trị ban đầu không hợp lệ

void setup() {
  Serial.begin(9600);
  Wire.begin();

  // Khởi tạo RTC
  if (!rtc.begin()) {
    Serial.println("RTC không tìm thấy!");
    while (1);
  }
  if (!rtc.isrunning()) {
    Serial.println("RTC không hoạt động, đang thiết lập thời gian!");
    rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
  }

  // Khởi tạo thẻ nhớ
  if (!SD.begin(chipSelect)) {
    Serial.println("Không thể khởi tạo thẻ SD!");
    while (1);
  }
  Serial.println("Thẻ SD đã được khởi tạo.");
}

void loop() {
  // Đọc giá trị điện áp từ cảm biến LM35
  int sensorValue = analogRead(LM35PIN);
  float voltage = sensorValue * (5.0 / 1023.0); // Chuyển đổi giá trị ADC sang điện áp (V)
  float temp = voltage * 100.0;                 // Chuyển đổi điện áp sang nhiệt độ (°C)

  // Kiểm tra lỗi cảm biến (nếu giá trị không hợp lệ)
  if (temp < -55 || temp > 150) { // LM35 chỉ hoạt động từ -55°C đến 150°C
    Serial.println("Không đọc được nhiệt độ từ cảm biến!");
    delay(1000); // Chờ 1 giây và thử lại
    return;
  }

  // Chỉ ghi nếu nhiệt độ thay đổi
  if (temp != previousTemp) {
    previousTemp = temp; // Cập nhật nhiệt độ mới nhất

    // Lấy thời gian hiện tại từ RTC
    DateTime now = rtc.now();
    String timeStamp = String(now.year()) + "/" + String(now.month()) + "/" + String(now.day()) + " " +
                       String(now.hour()) + ":" + String(now.minute()) + ":" + String(now.second());

    // Hiển thị thời gian và nhiệt độ lên Serial
    Serial.print("Thời gian: ");
    Serial.print(timeStamp);
    Serial.print(", Nhiệt độ: ");
    Serial.print(temp);
    Serial.println(" °C");

    // Ghi dữ liệu vào thẻ nhớ
    File file = SD.open("data1.txt", O_RDWR | O_CREAT | O_TRUNC); // Mở tệp ghi đè
    if (file) {
      file.print(timeStamp);
      file.print(", Temperature: ");
      file.println(temp);
      file.close();
      Serial.println("Dữ liệu đã được ghi vào thẻ SD.");
    } else {
      Serial.println("Không thể mở file để ghi.");
    }
  }

  delay(1000); // Chờ 1 giây trước khi kiểm tra lại
}