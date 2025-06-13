// Import the required libraries
#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <LittleFS.h>
#include <ArduinoJson.h>

// Define LED Pins
#define led1Pin 4 //D2
#define led2Pin 2 //D4

/* Put SSID & Password of your Router*/
const char* ssid = "daslearning";
const char* password = "123456789";

// Set the html file location
const char* htmlFile = "/index.html";

// led status on persistent storage for next every boot
const char* STAT_FILE = "/stat.json";
bool LED1Status;
bool LED2Status;
bool statChange = false;

// Define the webserver to handle requests
ESP8266WebServer server(80);

// Function to read the configuration from LittleFS
bool readStatFile() {
  File configFile = LittleFS.open(STAT_FILE, "r");
  if (!configFile) {
    Serial.println("Failed to open config file for reading. File might not exist.");
    return false;
  }

  size_t size = configFile.size();
  if (size == 0) {
    Serial.println("Config file is empty.");
    configFile.close();
    return false;
  }

  // JSON Doc object
  JsonDocument doc;

  // Deserialize the JSON document
  DeserializationError error = deserializeJson(doc, configFile);
  configFile.close(); // Close the file after reading
  if (error) {
    Serial.print(F("deserializeJson() failed: "));
    Serial.println(error.f_str());
    return false;
  }

  // Extract values from the JSON document
  LED1Status = doc["led1Status"].as<bool>();
  LED1Status = doc["led2Status"].as<bool>();
  return true;
}

// Persistent data for LED status: function
bool saveConfigFile() {
  File configFile = LittleFS.open(STAT_FILE, "w"); // Open in write mode, will create if not exists or overwrite
  if (!configFile) {
    Serial.println("Failed to open config file for writing.");
    return false;
  }

  JsonDocument doc; // json object

  // Populate the JSON document from the config struct
  doc["led1Status"] = LED1Status;
  doc["led2Status"] = LED2Status;

  // Serialize JSON to file
  if (serializeJson(doc, configFile) == 0) {
    Serial.println(F("Failed to write to file"));
    configFile.close();
    return false;
  }
  configFile.close();
  statChange = false;
  return true;
}

// On/Off API
void onOffApi() {
  if (server.hasArg("plain")) { // Check if there's a body to the request
    int ledNum;
    bool ledOn;
    String ledTxt;
    String msgToSend;
    String postBody = server.arg("plain"); // Get the raw body content

    JsonDocument doc; 

    // Parse the JSON string
    DeserializationError error = deserializeJson(doc, postBody);
    if (error) {
      Serial.print(F("deserializeJson() failed: "));
      Serial.println(error.f_str());
      server.send(400, "application/json", "{\"message\":\"Invalid JSON\"}"); // Send a bad request response
      return;
    }

    // Now you can access the JSON data
    if (doc.containsKey("ledNum")) {
      ledNum = doc["ledNum"].as<int>();
      if (doc.containsKey("ledOn")) {
        ledOn = doc["ledOn"].as<bool>();
        switch (ledNum) {
          case 1: // For LED1
            if(LED1Status != ledOn){
              LED1Status = ledOn;
              statChange = true;
            }
            break;
          case 2: // For LED2
            if(LED2Status != ledOn){
              LED2Status = ledOn;
              statChange = true;
            }
            break;
          default:
            msgToSend = "{\"message\":\"There is no LED number " + String(ledNum) + "in the system\"}";
            break;
        }
      }
      else{
        msgToSend = "{\"message\":\"The ledOn param not found in the request\"}";
      }
    }
    else {
      msgToSend = "{\"message\":\"The ledNum param not found in the request\"}";
    }
    // Send a response back to the client
    if(statChange){
      if(ledOn){
        ledTxt = "on";
      }
      else{
        ledTxt = "off";
      }
      msgToSend = "{\"message\":\"The LED no" + String(ledNum) + " has been turned " + ledTxt + "\"}";
      server.send(200, "application/json", msgToSend);
    }
    else{
      server.send(400, "application/json", msgToSend);
    }
  }
  else {
    server.send(400, "application/json", "{\"message\":\"No JSON data found in request body.\"}");
  }
}

// LED status checkup API
void getLedStat() {
  String msgToSend = "";
  String led1Txt = "";
  String led2Txt = "";

  if(LED1Status){
    led1Txt = "on";
  }
  else{
    led1Txt = "off";
  }
  if(LED2Status){
    led2Txt = "on";
  }
  else{
    led2Txt = "off";
  }
  msgToSend = "The LED no.1 is: " + led1Txt + " and LED no.2 is: " + led2Txt;

  JsonDocument doc;
  doc["led1"] = led1Txt;
  doc["led2"] = led2Txt;
  doc["message"] = msgToSend;
  String jsonResponse;
  serializeJson(doc, jsonResponse);

  server.send(200, "application/json", jsonResponse);
}

// Intialize the board
void setup() {

  // Set the serial console
  Serial.begin(115200);
  while (!Serial) continue;

  // Initialize the LittleFS
  Serial.println("Initializing LittleFS...");
  if (!LittleFS.begin()) {
    Serial.println("LittleFS Mount Failed!");
    return;
  }
  Serial.println("LittleFS Mounted Successfully.");

  // Start the Wifi
  Serial.println("Connecting to the WiFi network...");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi connected..!");
  Serial.print("Got IP: ");  
  Serial.println(WiFi.localIP());

  // Set the LED Pins
  pinMode(led1Pin, OUTPUT);
  pinMode(led2Pin, OUTPUT);

  // Read last status of LEDs
  if (readStatFile()) {
    Serial.println("Status file loaded successfully:");
  }
  else {
    Serial.println("\nFailed to load configuration. Using default values.");
    // Set some default values if the file couldn't be read or doesn't exist
    LED1Status = LOW;
    LED2Status = LOW;
    saveConfigFile();
  }

  // handle the server
  server.on("/", HTTP_GET, []() {
    File file = LittleFS.open("/index.html", "r"); // Open index.html for reading
    if (!file) {
      server.send(404, "text/plain", "File Not Found!");
      Serial.println("Failed to open index.html");
      return;
    }
    // Serve the file with correct content type
    server.streamFile(file, "text/html");
    file.close(); // Close the file after sending
  });
  server.on("/main.js", HTTP_GET, []() {
    File file = LittleFS.open("/main.js", "r"); // Open main.js for reading
    if (!file) {
      server.send(404, "text/plain", "File Not Found!");
      Serial.println("Failed to open index.html");
      return;
    }
    // Serve the file with correct content type
    server.streamFile(file, "text/js");
    file.close(); // Close the file after sending
  });
  // server api for led on/off
  server.on("/led/control", HTTP_POST, onOffApi);
  // status api
  server.on("/led/stat", HTTP_GET, getLedStat);
  server.begin();
  Serial.println(F("HTTP Server Started"));
}

// Main Loop
void loop() {
  server.handleClient();

  if(LED1Status) {
    digitalWrite(led1Pin, HIGH);
  }
  else {
    digitalWrite(led1Pin, LOW);
  }

  if(LED2Status) {
    digitalWrite(led2Pin, HIGH);
  }
  else {
    digitalWrite(led2Pin, LOW);
  }

  //if(statChange){
  //  saveConfigFile();
  //}
}