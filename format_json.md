// Gửi dữ liệu từ ESP32
String cardUID = "A1B2C3D4";
int gateType = 1; // 1=ENTRY, 0=EXIT
int parkingSlot = 5;

String jsonData = "{\"event\":\"CARD_SCAN\",\"uid\":\"" + cardUID + 
                  "\",\"gate\":\"" + (gateType ? "ENTRY" : "EXIT") + 
                  "\",\"slot\":" + String(parkingSlot) + "}";

Serial.println(jsonData);
