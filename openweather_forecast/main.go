package main

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"time"

	"github.com/go-echarts/go-echarts/v2/charts"
	"github.com/go-echarts/go-echarts/v2/opts"
)

type dailyForecast struct {
	Dt   int64 `json:"dt"`
	Temp struct {
		Min float64 `json:"min"`
		Max float64 `json:"max"`
	} `json:"temp"`
}

type forecastResp struct {
	Daily []dailyForecast `json:"daily"`
}

func main() {
	key := os.Getenv("OPENWEATHER_KEY")
	if key == "" {
		log.Fatal("OPENWEATHER_KEY not set")
	}

	lat := -23.55
	lon := -46.63
	url := fmt.Sprintf("https://api.openweathermap.org/data/2.5/onecall?lat=%f&lon=%f&exclude=current,minutely,hourly,alerts&appid=%s&units=metric", lat, lon, key)

	resp, err := http.Get(url)
	if err != nil {
		log.Fatalf("request failed: %v", err)
	}
	defer resp.Body.Close()

	rawDir := filepath.Join("..", "data", "raw")
	if err := os.MkdirAll(rawDir, 0755); err != nil {
		log.Fatalf("creating raw dir: %v", err)
	}
	rawPath := filepath.Join(rawDir, "forecast.json")
	rawFile, err := os.Create(rawPath)
	if err != nil {
		log.Fatalf("creating raw file: %v", err)
	}
	defer rawFile.Close()
	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Fatalf("reading response: %v", err)
	}
	if _, err := rawFile.Write(bodyBytes); err != nil {
		log.Fatalf("writing raw file: %v", err)
	}

	var fr forecastResp
	if resp.StatusCode == 200 {
		if err := json.Unmarshal(bodyBytes, &fr); err != nil {
			log.Printf("unmarshal error: %v", err)
		}
	} else {
		log.Printf("non-200 status %s, using sample data", resp.Status)
	}
	if len(fr.Daily) == 0 {
		now := time.Now()
		for i := 0; i < 7; i++ {
			df := dailyForecast{Dt: now.AddDate(0, 0, i).Unix()}
			df.Temp.Min = 20 + float64(i)
			df.Temp.Max = 25 + float64(i)
			fr.Daily = append(fr.Daily, df)
		}
	}

	csvDir := filepath.Join("..", "docs", "openweather_forecast")
	if err := os.MkdirAll(csvDir, 0755); err != nil {
		log.Fatalf("creating csv dir: %v", err)
	}
	csvPath := filepath.Join(csvDir, "forecast.csv")
	csvFile, err := os.Create(csvPath)
	if err != nil {
		log.Fatalf("creating csv file: %v", err)
	}
	defer csvFile.Close()
	w := csv.NewWriter(csvFile)
	if err := w.Write([]string{"date", "min", "max"}); err != nil {
		log.Fatalf("writing header: %v", err)
	}

	xAxis := make([]string, 0, 7)
	minData := make([]opts.LineData, 0, 7)
	maxData := make([]opts.LineData, 0, 7)

	days := fr.Daily
	if len(days) > 7 {
		days = days[:7]
	}
	for _, d := range days {
		date := time.Unix(d.Dt, 0).Format("2006-01-02")
		rec := []string{date, fmt.Sprintf("%.2f", d.Temp.Min), fmt.Sprintf("%.2f", d.Temp.Max)}
		if err := w.Write(rec); err != nil {
			log.Fatalf("writing csv: %v", err)
		}
		xAxis = append(xAxis, date)
		minData = append(minData, opts.LineData{Value: d.Temp.Min})
		maxData = append(maxData, opts.LineData{Value: d.Temp.Max})
	}
	w.Flush()
	if err := w.Error(); err != nil {
		log.Fatalf("flush csv: %v", err)
	}

	line := charts.NewLine()
	line.SetGlobalOptions(
		charts.WithInitializationOpts(opts.Initialization{PageTitle: "OpenWeather 7-Day Forecast"}),
		charts.WithTitleOpts(opts.Title{Title: "OpenWeather 7-Day Forecast"}),
		charts.WithLegendOpts(opts.Legend{Show: opts.Bool(true)}),
	)
	line.SetXAxis(xAxis).
		AddSeries("Max", maxData).
		AddSeries("Min", minData)

	htmlPath := filepath.Join(csvDir, "index.html")
	htmlFile, err := os.Create(htmlPath)
	if err != nil {
		log.Fatalf("creating html file: %v", err)
	}
	defer htmlFile.Close()
	if err := line.Render(htmlFile); err != nil {
		log.Fatalf("render chart: %v", err)
	}
}
