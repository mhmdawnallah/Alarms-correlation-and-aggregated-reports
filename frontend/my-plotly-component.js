import VuePlotly from 'vue-plotly'
import alarmsMapFigure from '../figures/alarms_map_figure.html'

export default {
  name: 'MyPlotlyComponent',
  components: {
    VuePlotly
  },
  data () {
    return {
      plotlyData: alarmsMapFigure
    }
  },
  template: `
    <div>
      <vue-plotly :plotlyData="plotlyData"></vue-plotly>
    </div>
  `
}
