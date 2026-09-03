package main

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestShellEndpoints(t *testing.T) {
	s, err := newServer("..")
	if err != nil {
		t.Fatal(err)
	}

	for _, test := range []struct {
		path        string
		contentType string
		body        string
	}{
		{"/", "text/html", "Energy Card Development Shell"},
		{"/apsystems_ezhi/apsystems-ezhi-energy-card.js", "text/javascript", "ApSystemsEzhiEnergyCard"},
		{"/api/device-registry", "application/json", deviceID},
		{"/api/entity-registry", "application/json", deviceUniqueID + "_pvP"},
		{"/api/states?scenario=alarm", "application/json", "\"state\":\"on\""},
	} {
		t.Run(test.path, func(t *testing.T) {
			recorder := httptest.NewRecorder()
			s.handler().ServeHTTP(recorder, httptest.NewRequest(http.MethodGet, test.path, nil))
			if recorder.Code != http.StatusOK {
				t.Fatalf("status = %d, want %d", recorder.Code, http.StatusOK)
			}
			if !strings.HasPrefix(recorder.Header().Get("Content-Type"), test.contentType) {
				t.Fatalf("Content-Type = %q, want prefix %q", recorder.Header().Get("Content-Type"), test.contentType)
			}
			if !strings.Contains(recorder.Body.String(), test.body) {
				t.Fatalf("body did not contain %q", test.body)
			}
		})
	}
}

func TestShellIncludesEditableInputs(t *testing.T) {
	s, err := newServer("..")
	if err != nil {
		t.Fatal(err)
	}
	recorder := httptest.NewRecorder()
	s.handler().ServeHTTP(recorder, httptest.NewRequest(http.MethodGet, "/", nil))
	for _, content := range []string{"Presets", "Inputs", "PV power (W)", "Active alarms", "BatHTP"} {
		if !strings.Contains(recorder.Body.String(), content) {
			t.Fatalf("shell did not include %q", content)
		}
	}
}

func TestStatesScenarios(t *testing.T) {
	if got := states("evening")["sensor.apsystems_ezhi_bat_p"]["state"]; got != "-420" {
		t.Fatalf("evening battery power = %q, want -420", got)
	}
	if got := states("offline")["sensor.apsystems_ezhi_pv_p"]["state"]; got != "unavailable" {
		t.Fatalf("offline PV state = %q, want unavailable", got)
	}
}
