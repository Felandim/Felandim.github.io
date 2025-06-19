package main

import (
	"archive/zip"
	"bytes"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"

	"gonum.org/v1/gonum/stat"

	"github.com/go-echarts/go-echarts/v2/charts"
	"github.com/go-echarts/go-echarts/v2/opts"
)

type Quote struct {
	Date  time.Time
	Close float64
}

func downloadZip(url string) ([]byte, error) {
	resp, err := http.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("bad status: %s", resp.Status)
	}
	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	return data, nil
}

func parseQuotes(r io.Reader, ticker string) ([]Quote, error) {
	var quotes []Quote
	buf := new(strings.Builder)
	if _, err := io.Copy(buf, r); err != nil {
		return nil, err
	}
	lines := strings.Split(buf.String(), "\n")
	for _, line := range lines {
		if len(line) < 170 {
			continue
		}
		if !strings.HasPrefix(line, "01") && !strings.HasPrefix(line, "02") {
			continue
		}
		if strings.TrimSpace(line[12:24]) != ticker {
			continue
		}
		dateStr := line[2:10]
		closeStr := line[108:121]
		date, err := time.Parse("20060102", dateStr)
		if err != nil {
			continue
		}
		price, err := strconv.ParseFloat(strings.TrimSpace(closeStr), 64)
		if err != nil {
			continue
		}
		price /= 100.0
		quotes = append(quotes, Quote{Date: date, Close: price})
	}
	sort.Slice(quotes, func(i, j int) bool { return quotes[i].Date.Before(quotes[j].Date) })
	return quotes, nil
}

func movingAverage(data []float64, window int) []float64 {
	ma := make([]float64, len(data))
	for i := range data {
		if i < window-1 {
			ma[i] = 0
			continue
		}
		ma[i] = stat.Mean(data[i-window+1:i+1], nil)
	}
	return ma
}

func sampleQuotes() []Quote {
	baseDate, _ := time.Parse("2006-01-02", "2024-01-01")
	qs := make([]Quote, 30)
	for i := range qs {
		qs[i] = Quote{
			Date:  baseDate.AddDate(0, 0, i),
			Close: 20 + float64(i)/10,
		}
	}
	return qs
}

func main() {
	const url = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A2024.ZIP"
	ticker := "PETR4"

	data, err := downloadZip(url)
	var quotes []Quote
	if err == nil {
		zr, err := zip.NewReader(bytes.NewReader(data), int64(len(data)))
		if err == nil {
			for _, f := range zr.File {
				rc, err := f.Open()
				if err != nil {
					continue
				}
				q, err := parseQuotes(rc, ticker)
				rc.Close()
				if err == nil {
					quotes = q
					break
				}
			}
		}
	}
	if len(quotes) == 0 {
		fmt.Println("using embedded sample data")
		quotes = sampleQuotes()
	}
	closes := make([]float64, len(quotes))
	for i, q := range quotes {
		closes[i] = q.Close
	}
	ma := movingAverage(closes, 21)

	xLabels := make([]string, len(quotes))
	closeData := make([]opts.LineData, len(quotes))
	maData := make([]opts.LineData, len(quotes))
	for i, q := range quotes {
		xLabels[i] = q.Date.Format("2006-01-02")
		closeData[i] = opts.LineData{Value: q.Close}
		if ma[i] > 0 {
			maData[i] = opts.LineData{Value: ma[i]}
		} else {
			maData[i] = opts.LineData{Value: nil}
		}
	}

	line := charts.NewLine()
	line.SetGlobalOptions(charts.WithTitleOpts(opts.Title{Title: "B3 Daily Prices " + ticker}))
	line.SetXAxis(xLabels).
		AddSeries("Close", closeData).
		AddSeries("MA21", maData)

	outDir := filepath.Join("..", "docs", "b3_prices")
	if err := os.MkdirAll(outDir, 0755); err != nil {
		panic(err)
	}
	f, err := os.Create(filepath.Join(outDir, "index.html"))
	if err != nil {
		panic(err)
	}
	defer f.Close()
	if err := line.Render(f); err != nil {
		panic(err)
	}
}
