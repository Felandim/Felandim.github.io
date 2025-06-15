const width = 960;
const height = 600;

const svg = d3.select('#map')
    .attr('viewBox', `0 0 ${width} ${height}`)
    .style('background', '#eef');

Promise.all([
    d3.json('https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json'),
    d3.json('public/data/co2.json')
]).then(([world, data]) => {
    const path = d3.geoPath();

    const dataByYear = d3.group(data, d => d.year);
    const maxVal = d3.max(data, d => d.co2_per_capita);
    const color = d3.scaleSequential(d3.interpolateOrRd)
        .domain([0, maxVal]);

    function draw(year) {
        const records = d3.index(dataByYear.get(year) || [], d => d.iso_code);
        const features = world.features;
        svg.selectAll('path')
            .data(features)
            .join('path')
            .attr('d', path)
            .attr('fill', d => {
                const rec = records.get(d.id);
                return rec ? color(rec.co2_per_capita) : '#ccc';
            })
            .attr('stroke', '#333');
    }

    const yearInput = d3.select('#year');
    const yearDisplay = d3.select('#year-value');

    function updateYear() {
        const y = +yearInput.property('value');
        yearDisplay.text(y);
        draw(y);
    }

    yearInput.on('input', updateYear);
    updateYear();
});
