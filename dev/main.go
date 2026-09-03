package main

import (
	"embed"
	"encoding/json"
	"flag"
	"html/template"
	"log"
	"net/http"
	"os"
	"path/filepath"
)

const (
	deviceID       = "ezhi-development-device"
	deviceUniqueID = "EZHI-DEV-001"
)

var (
	//go:embed templates/index.html
	templates embed.FS

	entityKeys = []string{
		"pvP", "ogP", "ofgP", "batP", "batSoc", "batTemp", "devTemp", "batS",
	}
	alarmKeys = []string{
		"BatHTP", "BatLTP", "BatCE", "BatHV", "BatLV", "BatHI", "BatE",
		"DTP", "EE", "SBS", "ACA", "OfOI", "PvHV", "PvOC", "IRDE",
		"PVWE", "OfGS", "VRP", "BCC", "BCI",
	}
)

type server struct {
	page       *template.Template
	cardScript string
}

type pageData struct {
	Measurements []stateInput
	Alarms       []stateInput
}

type stateInput struct {
	EntityID string
	Key      string
	Label    string
}

func main() {
	addr := flag.String("addr", ":8080", "HTTP listen address")
	root := flag.String("root", "..", "repository root")
	flag.Parse()

	s, err := newServer(*root)
	if err != nil {
		log.Fatal(err)
	}

	log.Printf("EZHI card shell available at http://localhost%s", *addr)
	log.Fatal(http.ListenAndServe(*addr, s.handler()))
}

func newServer(projectRoot string) (*server, error) {
	page, err := template.ParseFS(templates, "templates/index.html")
	if err != nil {
		return nil, err
	}

	cardScript := filepath.Join(projectRoot, "custom_components", "apsystems_ezhi", "frontend", "apsystems-ezhi-energy-card.js")
	cardScript, err = filepath.Abs(cardScript)
	if err != nil {
		return nil, err
	}
	if _, err := os.Stat(cardScript); err != nil {
		return nil, err
	}

	return &server{page: page, cardScript: cardScript}, nil
}

func (s *server) handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /", s.servePage)
	mux.HandleFunc("GET /apsystems_ezhi/apsystems-ezhi-energy-card.js", s.serveCard)
	mux.HandleFunc("GET /api/device-registry", serveJSON(deviceRegistry()))
	mux.HandleFunc("GET /api/entity-registry", serveJSON(entityRegistry()))
	mux.HandleFunc("GET /api/states", s.serveStates)
	return mux
}

func (s *server) servePage(w http.ResponseWriter, r *http.Request) {
	if err := s.page.ExecuteTemplate(w, "index.html", shellPageData()); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
	}
}

func shellPageData() pageData {
	labels := map[string]string{
		"pvP": "PV power (W)", "ogP": "On-grid power (W)", "ofgP": "Off-grid power (W)",
		"batP": "Battery power (W)", "batSoc": "Battery state of charge (%)",
		"batTemp": "Battery temperature (C)", "devTemp": "Device temperature (C)",
	}
	measurements := make([]stateInput, 0, len(entityKeys)-1)
	for _, key := range entityKeys {
		if key == "batS" {
			continue
		}
		measurements = append(measurements, stateInput{
			EntityID: entityID(key),
			Key:      key,
			Label:    labels[key],
		})
	}

	alarms := make([]stateInput, 0, len(alarmKeys))
	for _, key := range alarmKeys {
		alarms = append(alarms, stateInput{EntityID: entityID(key), Key: key, Label: key})
	}
	return pageData{Measurements: measurements, Alarms: alarms}
}

func (s *server) serveCard(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("Content-Type", "text/javascript; charset=utf-8")
	http.ServeFile(w, r, s.cardScript)
}

func (s *server) serveStates(w http.ResponseWriter, r *http.Request) {
	serveJSON(states(r.URL.Query().Get("scenario")))(w, r)
}

func serveJSON(value any) http.HandlerFunc {
	return func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		if err := json.NewEncoder(w).Encode(value); err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
		}
	}
}

func deviceRegistry() []map[string]any {
	return []map[string]any{{
		"id":          deviceID,
		"name":        "APsystems EZHI Development",
		"identifiers": [][]string{{"apsystems_ezhi", deviceUniqueID}},
	}}
}

func entityRegistry() []map[string]string {
	entities := make([]map[string]string, 0, len(entityKeys)+len(alarmKeys))
	for _, key := range append(entityKeys, alarmKeys...) {
		entities = append(entities, map[string]string{
			"device_id": deviceID,
			"entity_id": entityID(key),
			"unique_id": deviceUniqueID + "_" + key,
		})
	}
	return entities
}

func states(scenario string) map[string]map[string]string {
	values := map[string]string{
		"pvP": "620", "ogP": "180", "ofgP": "70", "batP": "170", "batSoc": "76",
		"batTemp": "27", "devTemp": "34", "batS": "charging",
	}
	switch scenario {
	case "evening":
		values = map[string]string{
			"pvP": "35", "ogP": "-290", "ofgP": "180", "batP": "-420", "batSoc": "62",
			"batTemp": "28", "devTemp": "31", "batS": "discharging",
		}
	case "idle":
		values = map[string]string{
			"pvP": "0", "ogP": "0", "ofgP": "0", "batP": "0", "batSoc": "76",
			"batTemp": "26", "devTemp": "29", "batS": "idle",
		}
	case "offline":
		values["pvP"] = "unavailable"
	case "alarm":
		values["DTP"] = "on"
	}

	result := make(map[string]map[string]string, len(entityKeys)+len(alarmKeys))
	for _, key := range entityKeys {
		result[entityID(key)] = map[string]string{"state": values[key]}
	}
	for _, key := range alarmKeys {
		state := "off"
		if values[key] == "on" {
			state = "on"
		}
		result[entityID(key)] = map[string]string{"state": state}
	}
	return result
}

func entityID(key string) string {
	return "sensor.apsystems_ezhi_" + snakeCase(key)
}

func snakeCase(value string) string {
	result := make([]rune, 0, len(value)+2)
	for i, char := range value {
		if i > 0 && char >= 'A' && char <= 'Z' {
			result = append(result, '_')
		}
		if char >= 'A' && char <= 'Z' {
			char += 'a' - 'A'
		}
		result = append(result, char)
	}
	return string(result)
}
