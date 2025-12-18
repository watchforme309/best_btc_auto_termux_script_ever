#include <M5Stack.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <ArduinoJson.h>
#include <mbedtls/sha256.h>

// ---------------- CONFIG ----------------
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

String BTC_ADDRESS = "32QLDQf4UNqCNJTKYBNXK2jzSnSctWfwc4";

struct Pool {
    const char* name;
    const char* host;
    uint16_t port;
    bool lotteryEnabled;
    uint32_t bestDiff;
    uint32_t acceptedShares;
    WiFiClient client;
    String workerName;
    String jobId;
    String jobData;
    uint32_t target;
};

Pool pools[] = {
    {"CKPOOL",  "solo.ckpool.org", 3333, true, 0, 0, WiFiClient(), "miner1", "", "", 0},
    {"ZSOLO",   "btc.zsolo.bid",   6057, true, 0, 0, WiFiClient(), "miner1", "", "", 0},
    {"ANTPOOL", "solo.antpool.com",3333, true, 0, 0, WiFiClient(), "miner1", "", "", 0},
    {"PUBLIC",  "public-pool.io", 21496,true, 0, 0, WiFiClient(), "miner1", "", "", 0}
};
const int NUM_POOLS = sizeof(pools)/sizeof(Pool);

// ---------------- UTILS ----------------
void sha256d(const uint8_t* input, size_t len, uint8_t output[32]){
    uint8_t temp[32];
    mbedtls_sha256(input,len,temp,0);
    mbedtls_sha256(temp,32,output,0);
}

uint32_t hashToDiff(uint8_t hash[32]){
    return ((uint32_t)hash[0]<<24) | ((uint32_t)hash[1]<<16) |
           ((uint32_t)hash[2]<<8) | (uint32_t)hash[3];
}

// ---------------- STRATUM ----------------
bool connectPool(Pool &p){
    if(!p.client.connect(p.host,p.port)) return false;

    // Subscribe
    DynamicJsonDocument doc(512);
    doc["id"] = 1;
    doc["method"] = "mining.subscribe";
    JsonArray arr = doc.createNestedArray("params");
    serializeJson(doc,doc["json"]);
    p.client.println(doc["json"].as<String>());

    // Authorize
    doc.clear();
    doc["id"] = 2;
    doc["method"] = "mining.authorize";
    arr = doc.createNestedArray("params");
    arr.add(BTC_ADDRESS);
    arr.add("");
    serializeJson(doc,doc["json"]);
    p.client.println(doc["json"].as<String>());

    return true;
}

// ---------------- MINER LOOP ----------------
void minePoolTask(void* param){
    Pool* p = (Pool*)param;
    uint8_t data[80];
    uint8_t hash[32];

    while(true){
        if(!p->client.connected()){
            connectPool(*p);
            delay(1000);
            continue;
        }

        // Process pool messages
        while(p->client.available()){
            String line = p->client.readStringUntil('\n');
            if(line.indexOf("mining.notify")!=-1){
                // Parse job ID and job data
                DynamicJsonDocument jobDoc(1024);
                deserializeJson(jobDoc,line);
                p->jobId = jobDoc["params"][0].as<String>();
                p->jobData = jobDoc["params"][1].as<String>();
                p->target = strtoul(jobDoc["params"][2], nullptr, 16);
            }
        }

        // Mining loop
        for(uint32_t nonce=0; nonce<0xFFFFFFFF; nonce++){
            // For demo: fill last 4 bytes with nonce
            for(int i=0;i<4;i++) data[76+i] = (nonce >> (8*(3-i))) & 0xFF;

            sha256d(data,80,hash);
            uint32_t diff = hashToDiff(hash);

            if(p->lotteryEnabled && (diff % 1000000 == 0)){
                p->acceptedShares++;
            }

            if(diff > p->bestDiff) p->bestDiff = diff;

            // Real submission (simplified)
            if(diff >= p->target){
                DynamicJsonDocument subDoc(512);
                subDoc["id"]=4;
                subDoc["method"]="mining.submit";
                JsonArray arr = subDoc.createNestedArray("params");
                arr.add(BTC_ADDRESS);
                arr.add(p->jobId);
                arr.add(""); // extranonce
                arr.add(String(nonce,16));
                arr.add(""); // time
                serializeJson(subDoc,line);
                p->client.println(line);
                p->acceptedShares++;
            }
        }
    }
}

// ---------------- DASHBOARD ----------------
void showDashboard(){
    M5.Lcd.fillScreen(BLACK);
    M5.Lcd.setCursor(0,0);
    M5.Lcd.setTextSize(2);
    M5.Lcd.printf("BTC: %s\n",BTC_ADDRESS.c_str());
    for(int i=0;i<NUM_POOLS;i++){
        M5.Lcd.printf("%s\n", pools[i].name);
        M5.Lcd.printf("Best Diff: %u\n",pools[i].bestDiff);
        M5.Lcd.printf("Accepted: %u\n",pools[i].acceptedShares);
        M5.Lcd.printf("Lottery: %s\n\n", pools[i].lotteryEnabled?"ON":"OFF");
    }
}

// ---------------- SETUP ----------------
void setup(){
    M5.begin();
    M5.Lcd.fillScreen(BLACK);

    WiFi.begin(ssid,password);
    M5.Lcd.setCursor(0,0);
    M5.Lcd.println("Connecting WiFi...");
    while(WiFi.status()!=WL_CONNECTED){
        delay(500);
        M5.Lcd.print(".");
    }
    M5.Lcd.println("\nWiFi Connected");

    for(int i=0;i<NUM_POOLS;i++){
        xTaskCreate(
            minePoolTask,
            pools[i].name,
            8192,
            &pools[i],
            1,
            NULL
        );
        delay(100);
    }
}

// ---------------- LOOP ----------------
void loop(){
    showDashboard();
    delay(1000);
}
