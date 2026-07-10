// pulse_timer
//
// Times the gap between pulses on a GPIO and prints one line per interval as
//   pulse_index dt_us
//
// Nothing here is specific to one detector. Any source with an active low pulse output works.
// I wrote it against a GGreg20_V3, which pulls the line up itself, so the pin is a plain INPUT
// and I trigger on the falling edge. There is no debounce on purpose. Debouncing would take the
// short interval tail, which is the part of the distribution I want to measure.
//
// Wiring: GGreg20 OUT to GPIO4, GGreg20 GND to ESP32 GND, GGreg20 BAT to ESP32 VIN and GND.
//
// The ISR to loop() handoff used to be a hand rolled ring buffer guarded with noInterrupts().
// noInterrupts() only masks the core that calls it, and on a dual core ESP32 the interrupt can
// land on the other one, so loop() could spin on a stale head or tail and reprint one interval
// thousands of times. A FreeRTOS queue replaces the ring buffer: xQueueSendFromISR and
// xQueueReceive carry the memory barriers a cross core handoff needs, so nothing is hand rolled.

const int PULSE_PIN = 4;
const int BAUD = 115200;
const int QUEUE_LEN = 256;

static QueueHandle_t pulseQueue;
static portMUX_TYPE dropMux = portMUX_INITIALIZER_UNLOCKED;   // guards dropped, the one counter still shared by hand

volatile uint32_t lastMicros = 0;
volatile bool seenFirst = false;
volatile uint32_t dropped = 0;

uint32_t pulseIndex = 0;

void IRAM_ATTR onPulse() {
  /* Runs on every falling edge. Pushes the gap since the previous edge onto the queue and returns. */
  uint32_t now = micros();
  if (!seenFirst) {
    // the first edge has no predecessor, so there is no interval to record yet
    lastMicros = now;
    seenFirst = true;
    return;
  }
  uint32_t dt = now - lastMicros;   // unsigned math, so this stays correct when micros wraps
  lastMicros = now;

  BaseType_t woken = pdFALSE;
  if (xQueueSendFromISR(pulseQueue, &dt, &woken) != pdTRUE) {
    // the queue is full, so I count the loss rather than block the ISR or overwrite an older interval
    portENTER_CRITICAL_ISR(&dropMux);
    dropped++;
    portEXIT_CRITICAL_ISR(&dropMux);
  }
  if (woken == pdTRUE) {
    portYIELD_FROM_ISR();
  }
}

void setup() {
  /* Bring up serial, the queue, and arm the interrupt */
  Serial.begin(BAUD);
  pulseQueue = xQueueCreate(QUEUE_LEN, sizeof(uint32_t));
  pinMode(PULSE_PIN, INPUT);   // no internal pullup, the GGreg20 provides one
  attachInterrupt(digitalPinToInterrupt(PULSE_PIN), onPulse, FALLING);
  Serial.println("# pulse_timer ready");
}

void loop() {
  /* Drain the queue to serial. Printing here keeps the ISR short. */
  uint32_t dt;
  while (xQueueReceive(pulseQueue, &dt, 0) == pdTRUE) {
    pulseIndex++;
    Serial.print(pulseIndex);
    Serial.print(' ');
    Serial.println(dt);
  }

  portENTER_CRITICAL(&dropMux);
  uint32_t lost = dropped;
  dropped = 0;
  portEXIT_CRITICAL(&dropMux);
  if (lost > 0) {
    Serial.print("# dropped ");
    Serial.println(lost);
  }
}
