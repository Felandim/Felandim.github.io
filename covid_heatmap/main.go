package main

import (
	"encoding/csv"
	"fmt"
	"io"
	"io/ioutil"
	"net/http"
	"os"
	"sort"
	"strconv"

	"github.com/ajstarks/svgo"
	"github.com/paulmach/go.geojson"
)

// population per state as of 2019 (IBGE)
var population = map[string]int{
	"AC": 881935,
	"AL": 3337357,
	"AM": 4144597,
	"AP": 845731,
	"BA": 14873064,
	"CE": 9132078,
	"DF": 3015268,
	"ES": 4018650,
	"GO": 7018354,
	"MA": 7075181,
	"MG": 21168791,
	"MS": 2778986,
	"MT": 3484466,
	"PA": 8602865,
	"PB": 4018127,
	"PE": 9557071,
	"PI": 3273227,
	"PR": 11433957,
	"RJ": 17264943,
	"RN": 3506853,
	"RO": 1777225,
	"RR": 605761,
	"RS": 11377239,
	"SC": 7164788,
	"SE": 2298696,
	"SP": 45919049,
	"TO": 1572866,
}

func fetchCases() (map[string]int, error) {
	url := "https://raw.githubusercontent.com/wcota/covid19br/master/cases-brazil-states.csv"
	resp, err := http.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	r := csv.NewReader(resp.Body)
	r.FieldsPerRecord = -1
	header, err := r.Read()
	if err != nil {
		return nil, err
	}
	// indices
	idxState, idxCity, idxCases := -1, -1, -1
	for i, field := range header {
		switch field {
		case "state":
			idxState = i
		case "city":
			idxCity = i
		case "totalCases":
			idxCases = i
		}
	}
	cases := map[string]int{}
	for {
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, err
		}
		if rec[idxCity] != "TOTAL" {
			continue
		}
		state := rec[idxState]
		c, _ := strconv.Atoi(rec[idxCases])
		cases[state] = c // keep last occurrence (latest date)
	}
	return cases, nil
}

func readGeoJSON(path string) (*geojson.FeatureCollection, error) {
	data, err := ioutil.ReadFile(path)
	if err != nil {
		return nil, err
	}
	return geojson.UnmarshalFeatureCollection(data)
}

func colorFor(value, max float64) string {
	if max == 0 {
		return "#ffffff"
	}
	ratio := value / max
	r := 255
	g := int(238 - ratio*238)
	b := int(238 - ratio*238)
	return fmt.Sprintf("#%02x%02x%02x", r, g, b)
}

func main() {
	cases, err := fetchCases()
	if err != nil {
		panic(err)
	}

	features, err := readGeoJSON("brazil-states.geojson")
	if err != nil {
		panic(err)
	}

	// compute cases per 100k and find max
	per100k := map[string]float64{}
	maxVal := 0.0
	for state, c := range cases {
		pop, ok := population[state]
		if !ok || pop == 0 {
			continue
		}
		val := float64(c) * 100000 / float64(pop)
		per100k[state] = val
		if val > maxVal {
			maxVal = val
		}
	}

	// compute map bounds
	minLon, maxLon := 180.0, -180.0
	minLat, maxLat := 90.0, -90.0
	for _, f := range features.Features {
		if f.Geometry == nil {
			continue
		}
		for _, poly := range f.Geometry.MultiPolygon {
			for _, ring := range poly {
				for _, coord := range ring {
					lon := coord[0]
					lat := coord[1]
					if lon < minLon {
						minLon = lon
					}
					if lon > maxLon {
						maxLon = lon
					}
					if lat < minLat {
						minLat = lat
					}
					if lat > maxLat {
						maxLat = lat
					}
				}
			}
		}
	}

	width, height := 1000, 1000

	outputDir := "../docs/covid_heatmap"
	os.MkdirAll(outputDir, 0755)
	svgFile, err := os.Create(outputDir + "/index.html")
	if err != nil {
		panic(err)
	}
	defer svgFile.Close()

	fmt.Fprintln(svgFile, "<!DOCTYPE html><html><head><meta charset='utf-8'><title>COVID-19 Brasil Heatmap</title></head><body>")
	canvas := svg.New(svgFile)
	canvas.Start(width, height)

	// sort features to ensure deterministic output
	sort.Slice(features.Features, func(i, j int) bool {
		si := features.Features[i].Properties["sigla"].(string)
		sj := features.Features[j].Properties["sigla"].(string)
		return si < sj
	})

	for _, f := range features.Features {
		state, ok := f.Properties["sigla"].(string)
		if !ok {
			continue
		}
		val := per100k[state]
		color := colorFor(val, maxVal)

		var pathData string
		for _, poly := range f.Geometry.MultiPolygon {
			for _, ring := range poly {
				for i, coord := range ring {
					x := int((coord[0] - minLon) / (maxLon - minLon) * float64(width))
					y := int(float64(height) - (coord[1]-minLat)/(maxLat-minLat)*float64(height))
					if i == 0 {
						pathData += fmt.Sprintf("M%d,%d", x, y)
					} else {
						pathData += fmt.Sprintf("L%d,%d", x, y)
					}
				}
				pathData += "z"
			}
		}
		canvas.Path(pathData, fmt.Sprintf("fill:%s;stroke:#000;stroke-width:0.5", color))
	}

	canvas.End()
	fmt.Fprintln(svgFile, "</body></html>")
}
