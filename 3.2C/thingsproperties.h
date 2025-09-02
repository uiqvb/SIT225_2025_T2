#include <ArduinoIoTCloud.h>
#include <Arduino_ConnectionHandler.h>

// Wi-Fi credentials
const char SSID[]     = "S23 FE";
const char PASS[]     = "manit1234";

// Network connection
WiFiConnectionHandler ArduinoIoTPreferredConnection(SSID, PASS);

// Cloud variables
bool impact_active;
bool impact_latch;
bool reset_request;

void initProperties() {
  ArduinoCloud.addProperty(impact_active, READ, ON_CHANGE, NULL);
  ArduinoCloud.addProperty(impact_latch, READ, ON_CHANGE, NULL);
  ArduinoCloud.addProperty(reset_request, READWRITE, ON_CHANGE, NULL);
}
