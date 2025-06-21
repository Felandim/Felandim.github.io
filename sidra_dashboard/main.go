package main

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strconv"
	"time"

	"github.com/go-echarts/go-echarts/v2/charts"
	"github.com/go-echarts/go-echarts/v2/components"
	"github.com/go-echarts/go-echarts/v2/opts"
	"github.com/go-resty/resty/v2"
)

type RawEntry map[string]string

type Data struct {
	Date    time.Time
	Monthly float64
	Acc12   float64
}

func main() {
	end := time.Now().AddDate(0, -1, 0)
	endStr := fmt.Sprintf("%d%02d", end.Year(), int(end.Month()))
	url := fmt.Sprintf("https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/63/p/201001-%s?formato=json", endStr)

	client := resty.New()
	resp, err := client.R().SetHeader("Accept", "application/json").Get(url)
	if err != nil {
		log.Fatalf("request failed: %v", err)
	}

	var raw []RawEntry
	if err := json.Unmarshal(resp.Body(), &raw); err != nil {
		log.Fatalf("unmarshal: %v", err)
	}
	if len(raw) <= 1 {
		log.Fatal("no data returned")
	}

	var series []Data
	for _, item := range raw[1:] {
		code := item["D3C"]
		date, err := time.Parse("200601", code)
		if err != nil {
			continue
		}
		vStr := item["V"]
		v, err := strconv.ParseFloat(vStr, 64)
		if err != nil {
			continue
		}
		series = append(series, Data{Date: date, Monthly: v})
	}

	for i := range series {
		if i < 11 {
			continue
		}
		prod := 1.0
		for j := i - 11; j <= i; j++ {
			prod *= 1 + series[j].Monthly/100
		}
		series[i].Acc12 = (prod - 1) * 100
	}

	line := charts.NewLine()
	var xVals []string
	var monthly []opts.LineData
	var acc12 []opts.LineData
	for _, d := range series {
		xVals = append(xVals, d.Date.Format("2006-01"))
		monthly = append(monthly, opts.LineData{Value: fmt.Sprintf("%.2f", d.Monthly)})
		if d.Acc12 == 0 {
			acc12 = append(acc12, opts.LineData{Value: nil})
		} else {
			acc12 = append(acc12, opts.LineData{Value: fmt.Sprintf("%.2f", d.Acc12)})
		}
	}
	line.SetGlobalOptions(
		charts.WithTitleOpts(opts.Title{Title: "IPCA"}),
		charts.WithInitializationOpts(opts.Initialization{PageTitle: "SIDRA Inflation Dashboard"}),
		charts.WithLegendOpts(opts.Legend{Show: opts.Bool(true)}),
	)
	line.SetXAxis(xVals).
		AddSeries("Inflação mensal", monthly).
		AddSeries("Variação 12 meses", acc12)

	page := components.NewPage()
	page.AddCharts(line)

	outputDir := filepath.Join("..", "docs", "sidra_dashboard")
	if err := os.MkdirAll(outputDir, 0755); err != nil {
		log.Fatalf("mkdir: %v", err)
	}
	f, err := os.Create(filepath.Join(outputDir, "index.html"))
	if err != nil {
		log.Fatalf("create output: %v", err)
	}
	defer f.Close()
	if err := page.Render(f); err != nil {
		log.Fatalf("render: %v", err)
	}
}
