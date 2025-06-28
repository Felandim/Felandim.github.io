package main

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/PuerkitoBio/goquery"
	"github.com/go-echarts/go-echarts/v2/charts"
	"github.com/go-echarts/go-echarts/v2/opts"
)

var fallbackTitles = []string{
	"After Dark in Central Park",
	"Boarding School Girls' Pajama Parade",
	"Buffalo Bill's Wild West Parad",
	"Caught",
	"Clowns Spinning Hats",
	"Capture of Boer Battery by British",
	"The Enchanted Drawing",
	"Feeding Sea Lions",
	"How to Make a Fat Wife Out of Two Lean Ones",
	"New Life Rescue",
	"New Morning Bath",
	"Searching Ruins on Broadway, Galveston, for Dead Bodies",
	"Sherlock Holmes Baffled",
	"The Tribulations of an Amateur Photographer",
	"Trouble in Hogan's Alley",
	"Two Old Sparks",
	"The Wonder, Ching Ling Foo",
	"Watermelon Contest",
	"Acrobats in Cairo",
	"An Affair of Honor",
	"Another Job for the Undertaker",
	"Arrival of Tongkin Train",
	"The Artist's Dilemma",
	"Band and Battalion of the U.S. Indian School",
	"Barnum and Bailey's Circus",
	"Beef Extract Room",
	"Boxing in Barrels",
	"Branding Hams",
	"Buffalo Street Parade",
	"A Busy Corner at Armour's",
	"The Bund, Shanghai",
	"Circular Panorama of the Base of the Electric Tower, Ending Looking Down the Mall",
	"Circular Panorama of the Electric Tower and Pond",
	"Circular Panorama of the Esplanade with the Electric Tower in the Background",
	"Coaling a Steamer, Nagasaki Bay, Japan",
	"Convention of Railroad Passengers",
	"Cornell-Columbia-University of Pennsylvania Boat Race at Ithaca, N.Y., Showing Lehigh Valley Observation Train",
	"Couchee Dance on the Midway",
	"The Donkey Party",
	"The Finish of Bridget McKeen",
	"Follow the Leader",
	"The Fraudulent Beggar",
	"Fun at a Children's Party",
	"A Good Joke",
	"The Gordon Sisters Boxing",
	"Grand Entry, Indian Congress",
	"Happy Hooligan April-Fooled",
	"Happy Hooligan Surprised",
	"Harbor of Shanghai",
	"A Hold-Up",
	"Ice-Boat Racing at Redbank, N.J.",
	"Indians No. 1",
	"Jeffries and Ruhlin Sparring Contest at San Francisco, Cal., November 15, 1901",
	"A Joke on Grandma",
	"Kansas Saloon Smashers",
	"Launching of the New Battleship 'Ohio' at San Francisco, Cal. When President McKinley Was There",
	"Laura Comstock's Bag-Punching Dog",
	"The Life of a Fireman",
	"Love by the Light of the Moon",
	"The Martyred Presidents",
	"Midway Dance",
	"Miles Canyon Tramway",
	"Montreal Fire Department on Runners",
	"Mounted Police Charge",
	"The Old Maid Having Her Picture Taken",
	"Opening of the Pan-American Exposition Showing Vice President Roosevelt Leading the Procession",
	"Pan-American Exposition by Night",
	"Panorama of the Exposition, No. 1",
	"Panorama of the Exposition, No. 2",
	"Panoramic View of the Fleet After Yacht Race",
	"Panoramic View of the Temple of Music and Esplanade",
	"Panoramic View, Asheville, N.C.",
	"Le Petit chaperon rouge",
	"Photographing the Audience",
	"Pie, Tramp and the Bulldog",
	"President McKinley and Escort Going to the Capitol",
	"President McKinley Taking the Oath",
	"President McKinley's Speech at the Pan-American Exposition",
	"The Queen's Funeral",
	"Le Rêve de Noël",
	"Rocking Gold in the Klondike",
	"Ruhlin in His Training Quarters",
	"Shad Fishing at Gloucester, N.J.",
	"Terrible Teddy, the Grizzly King",
	"The Tramp's Dream",
	"Tramp's Nap Interrupted",
	"Trapeze Disrobing Act",
	"A Trip Around the Pan-American Exposition",
	"Turkish Dance",
	"Twelve in a Barrel",
	"Two Rubes at the Theatre",
	"Upper Falls of the Yellowstone",
	"Washing Gold on 20 Above Hunker, Klondike",
	"Wedding Procession in Cairo",
	"Why Mr. Nation Wants a Divorce",
	"Wonderful Trick Donkey, The",
	"Yacht Race Fleet Following the Committee Boat 'Navigator' Oct. 4th, The",
	"You Can't Lose Your Mother-in-Law",
	"Pyrate Bay",
	"Arrival of Prince Henry (of Prussia) and President Roosevelt at Shooter's Island (1902)",
}

var stopwords = map[string]struct{}{
	"the": {}, "and": {}, "for": {}, "are": {}, "but": {}, "not": {}, "with": {}, "you": {}, "your": {}, "was": {},
	"this": {}, "that": {}, "from": {}, "into": {}, "have": {}, "has": {}, "had": {}, "his": {}, "her": {}, "she": {}, "him": {}, "its": {}, "our": {}, "one": {}, "two": {}, "who": {}, "all": {}, "off": {}, "new": {}, "old": {}, "mrs": {}, "mr": {},
	"of": {}, "in": {}, "to": {}, "a": {}, "an": {}, "on": {}, "at": {}, "by": {}, "or": {}, "is": {}, "la": {}, "de": {}, "el": {}, "da": {}, "do": {}, "los": {}, "las": {}, "um": {}, "uma": {},
}

func fetchTitles() ([]string, error) {
	req, err := http.NewRequest("GET", "https://www.imdb.com/chart/top", nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", "Mozilla/5.0")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("status %s", resp.Status)
	}
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(string(body)))
	if err != nil {
		return nil, err
	}
	var titles []string
	doc.Find("tbody.lister-list tr").EachWithBreak(func(i int, s *goquery.Selection) bool {
		if i >= 100 {
			return false
		}
		t := strings.TrimSpace(s.Find("td.titleColumn a").Text())
		if t != "" {
			titles = append(titles, t)
		}
		return true
	})
	if len(titles) == 0 {
		return nil, fmt.Errorf("no titles parsed")
	}
	return titles, nil
}

func wordFreq(titles []string) map[string]int {
	freq := make(map[string]int)
	re := regexp.MustCompile(`[A-Za-z']+`)
	for _, t := range titles {
		for _, w := range re.FindAllString(strings.ToLower(t), -1) {
			if len(w) < 3 {
				continue
			}
			if _, ok := stopwords[w]; ok {
				continue
			}
			freq[w]++
		}
	}
	return freq
}

func main() {
	titles, err := fetchTitles()
	if err != nil {
		fmt.Println("using embedded sample titles")
		titles = fallbackTitles
	}

	freq := wordFreq(titles)

	wcData := make([]opts.WordCloudData, 0, len(freq))
	for w, c := range freq {
		wcData = append(wcData, opts.WordCloudData{Name: w, Value: c})
	}

	wc := charts.NewWordCloud()
	wc.SetGlobalOptions(
		charts.WithInitializationOpts(opts.Initialization{PageTitle: "IMDb Top 100 Word Cloud"}),
		charts.WithTitleOpts(opts.Title{Title: "IMDb Top 100 Word Cloud"}),
	)
	wc.AddSeries("words", wcData)

	outDir := filepath.Join("..", "docs", "imdb_wordcloud")
	if err := os.MkdirAll(outDir, 0755); err != nil {
		panic(err)
	}
	f, err := os.Create(filepath.Join(outDir, "index.html"))
	if err != nil {
		panic(err)
	}
	defer f.Close()
	if err := wc.Render(f); err != nil {
		panic(err)
	}
}
