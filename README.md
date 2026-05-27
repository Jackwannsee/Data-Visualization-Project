# CS:GO Demo Analyzer
A comprehensive data visualization project for analyzing professional CS:GO demo files. This project provides tools for parsing, processing, visualizing, and creating interactive dashboards from .dem files.


- Clarity of the research question / motivation and / or relevance (6)
- Data mining (0-5) - will be 0 when downloading a structured dataset from a resource like Kaggle
- Data cleaning (0-5) - will be 0 if no data transformation, imputation etc. was necessary
- Visualization design / infographics design (7-12) - will be a maximum of 7 points when using traditional charts (e.g., bar charts and scatterplots from a Python visualization library) in an appropriate, effective, and expressive way; can be higher when more thought went into the visual encoding (e.g., applying non-standard but interesting data transformations, a smart combination of different visual encodings, interesting infographic design, engaging and insightful use of animation, non-straight-forward visual encoding choice that leads to an interesting visual result, ...)
- Interaction design (0-10) - will be 0 when the visualizations are static, up to 5 points when using traditional interaction techniques like zooming or brushing and linking; can be higher for more interesting solutions (e.g., interesting semantic zooming solutions, non-standard but useful ways to query the data, ...)
- Implementation (0-10) - will be 0 when using standard visualization libraries, up to 5 points when intelligently using non-standard out-of-the-box solutions (e.g., parallelized data frames), but can be up to 10 points when tackling difficult implementation issues (e.g., scalability issues using approaches that cannot be tackled with out-of-the-box solutions, smart integration of model predictions) 
- Question answering / conclusions / findings (~ analysis results) (7) 




Tick downsampling: Keep every 16th tick (128 ticks/s → 8 samples/s) to reduce 1.5M rows/demo to ~95K while preserving positioning patterns

## TODO
- [x] Rounds won dataset
- [x] Green and Red win / lose colors to be changed (Economy Chart)
- [x] Add overtime line to economy viz chart.
- [ ] on the dashboard change year from 2025 to 2026
- [x] On the dashboard have a brackets result, where you can click on a match and review the stats from that match. 
- [x] Heatmap for player movements (use own heatmap calculation software?)
- [ ] Spider charts for:
    - Which maps the different teams played 
    - Statistics such as util thrown, this can be highlighted during CT and T (see if molotovs are thrown more during T as they are stronger)
    - KAST statistics for individual players, to determine the strongest players with most impact
- [x] Economy Charts, line chart for each game where the individual economies are highlighted. (how to overlay with who won that game)
- [x] on the streamlit homepage, have an overview of the budapest major alongside the tree map of the final 
- [ ] Player performance spider chart should default to `both`
- [ ] Diverging bar plot player stats on ct and t maybe do rounds won per map? have the map name in the middle and then the diverging aspect.
- [ ] Check the descriptions and whether they are relevant and correct
- [ ] Create MD file for data_processing
- [ ] Create MD file for visualization
- [x] Heatmap on CT side includes the spawn area... Watch out with simply removing the spawn area as this affects overpass
- [x] Streamlit missing heatmap page link on individual other pages.
