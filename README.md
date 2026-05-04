# CS:GO Demo Analyzer

A comprehensive data visualization project for analyzing professional CS:GO demo files. This project provides tools for parsing, processing, visualizing, and creating interactive dashboards from .dem files.


vibe --resume deb42c56


## TODO
- Rounds won dataset
- is it possible to 


## Visualization Ideas
- On the dashboard have a brackets result, where you can click on a match and review the stats from that match. 
- Heatmap for player movements (use own heatmap calculation software?)
- Spider charts for:
    - Which maps the different teams played 
    - Statistics such as util thrown, this can be highlighted during CT and T (see if molotovs are thrown more during T as they are stronger)
    - KAST statistics for individual players, to determine the strongest players with most impact
    - 
- Economy Charts, line chart for each game where the individual economies are highlighted. (how to overlay with who won that game)


## Improvements
- `parse_outcomes.py` can be made more efficient by changing it from individual player wins to team aggregate wins 