package main

import (
	"encoding/csv"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"gonum.org/v1/gonum/stat"

	"github.com/go-echarts/go-echarts/v2/charts"
	"github.com/go-echarts/go-echarts/v2/opts"
)

const dataCSV = `
1949-01,112
1949-02,118
1949-03,132
1949-04,129
1949-05,121
1949-06,135
1949-07,148
1949-08,148
1949-09,136
1949-10,119
1949-11,104
1949-12,118
1950-01,115
1950-02,126
1950-03,141
1950-04,135
1950-05,125
1950-06,149
1950-07,170
1950-08,170
1950-09,158
1950-10,133
1950-11,114
1950-12,140
1951-01,145
1951-02,150
1951-03,178
1951-04,163
1951-05,172
1951-06,178
1951-07,199
1951-08,199
1951-09,184
1951-10,162
1951-11,146
1951-12,166
1952-01,171
1952-02,180
1952-03,193
1952-04,181
1952-05,183
1952-06,218
1952-07,230
1952-08,242
1952-09,209
1952-10,191
1952-11,172
1952-12,194
1953-01,196
1953-02,196
1953-03,236
1953-04,235
1953-05,229
1953-06,243
1953-07,264
1953-08,272
1953-09,237
1953-10,211
1953-11,180
1953-12,201
1954-01,204
1954-02,188
1954-03,235
1954-04,227
1954-05,234
1954-06,264
1954-07,302
1954-08,293
1954-09,259
1954-10,229
1954-11,203
1954-12,229
1955-01,242
1955-02,233
1955-03,267
1955-04,269
1955-05,270
1955-06,315
1955-07,364
1955-08,347
1955-09,312
1955-10,274
1955-11,237
1955-12,278
1956-01,284
1956-02,277
1956-03,317
1956-04,313
1956-05,318
1956-06,374
1956-07,413
1956-08,405
1956-09,355
1956-10,306
1956-11,271
1956-12,306
1957-01,315
1957-02,301
1957-03,356
1957-04,348
1957-05,355
1957-06,422
1957-07,465
1957-08,467
1957-09,404
1957-10,347
1957-11,305
1957-12,336
1958-01,340
1958-02,318
1958-03,362
1958-04,348
1958-05,363
1958-06,435
1958-07,491
1958-08,505
1958-09,404
1958-10,359
1958-11,310
1958-12,337
1959-01,360
1959-02,342
1959-03,406
1959-04,396
1959-05,420
1959-06,472
1959-07,548
1959-08,559
1959-09,463
1959-10,407
1959-11,362
1959-12,405
1960-01,417
1960-02,391
1960-03,419
1960-04,461
1960-05,472
1960-06,535
1960-07,622
1960-08,606
1960-09,508
1960-10,461
1960-11,390
1960-12,432
`

func main() {
	reader := csv.NewReader(strings.NewReader(dataCSV))
	records, err := reader.ReadAll()
	if err != nil {
		panic(err)
	}

	var dates []string
	var values []float64
	for _, rec := range records {
		dates = append(dates, rec[0])
		v, err := strconv.ParseFloat(rec[1], 64)
		if err != nil {
			panic(err)
		}
		values = append(values, v)
	}

	mean := stat.Mean(values, nil)
	std := stat.StdDev(values, nil)

	normalized := make([]float64, len(values))
	for i, v := range values {
		normalized[i] = (v - mean) / std
	}

	x := normalized[:len(normalized)-1]
	y := normalized[1:]
	phi := stat.Covariance(x, y, nil) / stat.Variance(x, nil)
	intercept := stat.Mean(y, nil) - phi*stat.Mean(x, nil)

	predNorm := make([]float64, len(normalized)+12)
	predNorm[0] = normalized[0]
	for i := 1; i < len(normalized); i++ {
		predNorm[i] = intercept + phi*normalized[i-1]
	}
	for i := len(normalized); i < len(predNorm); i++ {
		predNorm[i] = intercept + phi*predNorm[i-1]
	}

	predictions := make([]float64, len(predNorm))
	for i, v := range predNorm {
		predictions[i] = v*std + mean
	}

	allDates := make([]string, len(predictions))
	copy(allDates, dates)
	last := dates[len(dates)-1]
	year, _ := strconv.Atoi(last[:4])
	month, _ := strconv.Atoi(last[5:])
	for i := len(dates); i < len(predictions); i++ {
		month++
		if month > 12 {
			month = 1
			year++
		}
		allDates[i] = fmt.Sprintf("%04d-%02d", year, month)
	}

	line := charts.NewLine()
	line.SetGlobalOptions(
		charts.WithInitializationOpts(opts.Initialization{PageTitle: "AirPassengers – Real vs. Previsto"}),
		charts.WithTitleOpts(opts.Title{Title: "AirPassengers – Real vs. Previsto"}),
		charts.WithLegendOpts(opts.Legend{Show: opts.Bool(true)}),
	)
	line.SetXAxis(allDates)

	obs := make([]opts.LineData, len(predictions))
	for i := range obs {
		if i < len(values) {
			obs[i] = opts.LineData{Value: values[i]}
		} else {
			obs[i] = opts.LineData{Value: nil}
		}
	}
	pred := make([]opts.LineData, len(predictions))
	for i, v := range predictions {
		pred[i] = opts.LineData{Value: v}
	}

	line.AddSeries("Observado", obs)
	line.AddSeries("Previsto", pred)

	outDir := filepath.Join("..", "docs", "time_forecaster")
	os.MkdirAll(outDir, 0755)
	f, err := os.Create(filepath.Join(outDir, "index.html"))
	if err != nil {
		panic(err)
	}
	defer f.Close()
	line.Render(f)
}
