package main

import (
	"encoding/csv"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"gonum.org/v1/gonum/mat"
	"gonum.org/v1/gonum/stat"

	"github.com/go-echarts/go-echarts/v2/charts"
	"github.com/go-echarts/go-echarts/v2/opts"
)

const irisCSV = `
sepal_length,sepal_width,petal_length,petal_width,species
5.1,3.5,1.4,0.2,setosa
4.9,3,1.4,0.2,setosa
4.7,3.2,1.3,0.2,setosa
4.6,3.1,1.5,0.2,setosa
5,3.6,1.4,0.2,setosa
5.4,3.9,1.7,0.4,setosa
4.6,3.4,1.4,0.3,setosa
5,3.4,1.5,0.2,setosa
4.4,2.9,1.4,0.2,setosa
4.9,3.1,1.5,0.1,setosa
5.4,3.7,1.5,0.2,setosa
4.8,3.4,1.6,0.2,setosa
4.8,3,1.4,0.1,setosa
4.3,3,1.1,0.1,setosa
5.8,4,1.2,0.2,setosa
5.7,4.4,1.5,0.4,setosa
5.4,3.9,1.3,0.4,setosa
5.1,3.5,1.4,0.3,setosa
5.7,3.8,1.7,0.3,setosa
5.1,3.8,1.5,0.3,setosa
5.4,3.4,1.7,0.2,setosa
5.1,3.7,1.5,0.4,setosa
4.6,3.6,1,0.2,setosa
5.1,3.3,1.7,0.5,setosa
4.8,3.4,1.9,0.2,setosa
5,3,1.6,0.2,setosa
5,3.4,1.6,0.4,setosa
5.2,3.5,1.5,0.2,setosa
5.2,3.4,1.4,0.2,setosa
4.7,3.2,1.6,0.2,setosa
4.8,3.1,1.6,0.2,setosa
5.4,3.4,1.5,0.4,setosa
5.2,4.1,1.5,0.1,setosa
5.5,4.2,1.4,0.2,setosa
4.9,3.1,1.5,0.1,setosa
5,3.2,1.2,0.2,setosa
5.5,3.5,1.3,0.2,setosa
4.9,3.1,1.5,0.1,setosa
4.4,3,1.3,0.2,setosa
5.1,3.4,1.5,0.2,setosa
5,3.5,1.3,0.3,setosa
4.5,2.3,1.3,0.3,setosa
4.4,3.2,1.3,0.2,setosa
5,3.5,1.6,0.6,setosa
5.1,3.8,1.9,0.4,setosa
4.8,3,1.4,0.3,setosa
5.1,3.8,1.6,0.2,setosa
4.6,3.2,1.4,0.2,setosa
5.3,3.7,1.5,0.2,setosa
5,3.3,1.4,0.2,setosa
7,3.2,4.7,1.4,versicolor
6.4,3.2,4.5,1.5,versicolor
6.9,3.1,4.9,1.5,versicolor
5.5,2.3,4,1.3,versicolor
6.5,2.8,4.6,1.5,versicolor
5.7,2.8,4.5,1.3,versicolor
6.3,3.3,4.7,1.6,versicolor
4.9,2.4,3.3,1,versicolor
6.6,2.9,4.6,1.3,versicolor
5.2,2.7,3.9,1.4,versicolor
5,2,3.5,1,versicolor
5.9,3,4.2,1.5,versicolor
6,2.2,4,1,versicolor
6.1,2.9,4.7,1.4,versicolor
5.6,2.9,3.6,1.3,versicolor
6.7,3.1,4.4,1.4,versicolor
5.6,3,4.5,1.5,versicolor
5.8,2.7,4.1,1,versicolor
6.2,2.2,4.5,1.5,versicolor
5.6,2.5,3.9,1.1,versicolor
5.9,3.2,4.8,1.8,versicolor
6.1,2.8,4,1.3,versicolor
6.3,2.5,4.9,1.5,versicolor
6.1,2.8,4.7,1.2,versicolor
6.4,2.9,4.3,1.3,versicolor
6.6,3,4.4,1.4,versicolor
6.8,2.8,4.8,1.4,versicolor
6.7,3,5,1.7,versicolor
6,2.9,4.5,1.5,versicolor
5.7,2.6,3.5,1,versicolor
5.5,2.4,3.8,1.1,versicolor
5.5,2.4,3.7,1,versicolor
5.8,2.7,3.9,1.2,versicolor
6,2.7,5.1,1.6,versicolor
5.4,3,4.5,1.5,versicolor
6,3.4,4.5,1.6,versicolor
6.7,3.1,4.7,1.5,versicolor
6.3,2.3,4.4,1.3,versicolor
5.6,3,4.1,1.3,versicolor
5.5,2.5,4,1.3,versicolor
5.5,2.6,4.4,1.2,versicolor
6.1,3,4.6,1.4,versicolor
5.8,2.6,4,1.2,versicolor
5,2.3,3.3,1,versicolor
5.6,2.7,4.2,1.3,versicolor
5.7,3,4.2,1.2,versicolor
5.7,2.9,4.2,1.3,versicolor
6.2,2.9,4.3,1.3,versicolor
5.1,2.5,3,1.1,versicolor
5.7,2.8,4.1,1.3,versicolor
6.3,3.3,6,2.5,virginica
5.8,2.7,5.1,1.9,virginica
7.1,3,5.9,2.1,virginica
6.3,2.9,5.6,1.8,virginica
6.5,3,5.8,2.2,virginica
7.6,3,6.6,2.1,virginica
4.9,2.5,4.5,1.7,virginica
7.3,2.9,6.3,1.8,virginica
6.7,2.5,5.8,1.8,virginica
7.2,3.6,6.1,2.5,virginica
6.5,3.2,5.1,2,virginica
6.4,2.7,5.3,1.9,virginica
6.8,3,5.5,2.1,virginica
5.7,2.5,5,2,virginica
5.8,2.8,5.1,2.4,virginica
6.4,3.2,5.3,2.3,virginica
6.5,3,5.5,1.8,virginica
7.7,3.8,6.7,2.2,virginica
7.7,2.6,6.9,2.3,virginica
6,2.2,5,1.5,virginica
6.9,3.2,5.7,2.3,virginica
5.6,2.8,4.9,2,virginica
7.7,2.8,6.7,2,virginica
6.3,2.7,4.9,1.8,virginica
6.7,3.3,5.7,2.1,virginica
7.2,3.2,6,1.8,virginica
6.2,2.8,4.8,1.8,virginica
6.1,3,4.9,1.8,virginica
6.4,2.8,5.6,2.1,virginica
7.2,3,5.8,1.6,virginica
7.4,2.8,6.1,1.9,virginica
7.9,3.8,6.4,2,virginica
6.4,2.8,5.6,2.2,virginica
6.3,2.8,5.1,1.5,virginica
6.1,2.6,5.6,1.4,virginica
7.7,3,6.1,2.3,virginica
6.3,3.4,5.6,2.4,virginica
6.4,3.1,5.5,1.8,virginica
6,3,4.8,1.8,virginica
6.9,3.1,5.4,2.1,virginica
6.7,3.1,5.6,2.4,virginica
6.9,3.1,5.1,2.3,virginica
5.8,2.7,5.1,1.9,virginica
6.8,3.2,5.9,2.3,virginica
6.7,3.3,5.7,2.5,virginica
6.7,3,5.2,2.3,virginica
6.3,2.5,5,1.9,virginica
6.5,3,5.2,2,virginica
6.2,3.4,5.4,2.3,virginica
5.9,3,5.1,1.8,virginica
`

func main() {
	r := csv.NewReader(strings.NewReader(irisCSV))
	records, err := r.ReadAll()
	if err != nil {
		panic(err)
	}

	n := len(records) - 1
	data := mat.NewDense(n, 4, nil)
	species := make([]string, n)

	for i, row := range records {
		if i == 0 {
			continue
		}
		for j := 0; j < 4; j++ {
			v, err := strconv.ParseFloat(row[j], 64)
			if err != nil {
				panic(err)
			}
			data.Set(i-1, j, v)
		}
		species[i-1] = row[4]
	}

	// Standardize columns
	for j := 0; j < 4; j++ {
		col := mat.Col(nil, j, data)
		mean := stat.Mean(col, nil)
		std := stat.StdDev(col, nil)
		for i := range col {
			col[i] = (col[i] - mean) / std
		}
		data.SetCol(j, col)
	}

	var pc stat.PC
	ok := pc.PrincipalComponents(data, nil)
	if !ok {
		panic("PCA failed")
	}

	var vecs mat.Dense
	pc.VectorsTo(&vecs)
	proj := mat.NewDense(n, 2, nil)
	proj.Product(data, vecs.Slice(0, 4, 0, 2))

	bySpec := map[string][]opts.ScatterData{}
	for i := 0; i < n; i++ {
		point := opts.ScatterData{Value: []interface{}{proj.At(i, 0), proj.At(i, 1)}}
		sp := species[i]
		bySpec[sp] = append(bySpec[sp], point)
	}

	scatter := charts.NewScatter()
	scatter.SetGlobalOptions(
		charts.WithTitleOpts(opts.Title{Title: "Iris PCA"}),
		charts.WithXAxisOpts(opts.XAxis{Name: "PC1"}),
		charts.WithYAxisOpts(opts.YAxis{Name: "PC2"}),
	)

	for sp, pts := range bySpec {
		scatter.AddSeries(sp, pts)
	}

	// save HTML under repository docs directory
	outDir := filepath.Join("..", "docs", "iris_pca")
	if err := os.MkdirAll(outDir, 0755); err != nil {
		panic(err)
	}
	f, err := os.Create(filepath.Join(outDir, "index.html"))
	if err != nil {
		panic(err)
	}
	defer f.Close()
	if err := scatter.Render(f); err != nil {
		panic(err)
	}
}
