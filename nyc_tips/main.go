package main

import (
	"compress/gzip"
	"encoding/csv"
	"fmt"
	"io"
	"log"
	"math"
	"net/http"
	"os"
	"sort"
	"strconv"

	"gonum.org/v1/gonum/floats"
	"gonum.org/v1/gonum/stat"

	"github.com/go-echarts/go-echarts/v2/charts"
	"github.com/go-echarts/go-echarts/v2/opts"
)

func main() {
	url := "https://github.com/DataTalksClub/nyc-tlc-data/releases/download/yellow/yellow_tripdata_2019-01.csv.gz"

	resp, err := http.Get(url)
	if err != nil {
		log.Fatalf("failed to download data: %v", err)
	}
	defer resp.Body.Close()

	gz, err := gzip.NewReader(resp.Body)
	if err != nil {
		log.Fatalf("failed to create gzip reader: %v", err)
	}
	defer gz.Close()

	r := csv.NewReader(gz)
	header, err := r.Read()
	if err != nil {
		log.Fatalf("failed reading header: %v", err)
	}

	idx := -1
	for i, h := range header {
		if h == "tip_amount" {
			idx = i
			break
		}
	}
	if idx == -1 {
		log.Fatalf("tip_amount column not found")
	}

	var tips []float64
	maxRows := 1000000
	for len(tips) < maxRows {
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			log.Fatalf("error reading csv: %v", err)
		}
		if idx >= len(rec) {
			continue
		}
		val, err := parseFloat(rec[idx])
		if err != nil {
			continue
		}
		if math.IsNaN(val) {
			continue
		}
		if val < 0 {
			val = -val
		}
		tips = append(tips, val)
	}

	if len(tips) == 0 {
		log.Fatalf("no data read")
	}

	sort.Float64s(tips)

	bins := 30
	dividers := make([]float64, bins+1)
	min := 0.0
	max := floats.Max(tips) + 1.0
	floats.Span(dividers, min, max)
	counts := stat.Histogram(nil, dividers, tips, nil)

	categories := make([]string, bins)
	for i := 0; i < bins; i++ {
		categories[i] = fmt.Sprintf("%.2f-%.2f", dividers[i], dividers[i+1])
	}

	bar := charts.NewBar()
	bar.SetGlobalOptions(
		charts.WithInitializationOpts(opts.Initialization{PageTitle: "NYC Taxi Tip Histogram"}),
		charts.WithTitleOpts(opts.Title{Title: "Distribuição de Gorjetas – NYC Taxi"}),
	)
	bar.SetXAxis(categories)
	data := make([]opts.BarData, bins)
	for i, c := range counts {
		data[i] = opts.BarData{Value: c}
	}
	bar.AddSeries("Gorjetas", data)

	outDir := "../docs/nyc_tips"
	if err := os.MkdirAll(outDir, 0755); err != nil {
		log.Fatalf("failed creating output dir: %v", err)
	}
	f, err := os.Create(outDir + "/index.html")
	if err != nil {
		log.Fatalf("failed creating output file: %v", err)
	}
	defer f.Close()
	if err := bar.Render(f); err != nil {
		log.Fatalf("failed rendering chart: %v", err)
	}
}

func parseFloat(s string) (float64, error) {
	if s == "" {
		return 0, fmt.Errorf("empty")
	}
	v, err := strconv.ParseFloat(s, 64)
	if err != nil {
		return 0, err
	}
	return v, nil
}
