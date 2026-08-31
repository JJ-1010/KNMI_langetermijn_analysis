# KNMI_langetermijn_analysis
Checks the longterm weather forecast for the Netherlands and compares the results of T+1 days with forecasts up to T+13.
For example; On the January 1st, a forecast was made up to the 14th, The forecast on the 13th (for the day after) was taken as a true value and all dates before, that forecast the 14th of January, are compared to it.

Uses the KNMI official API; you need an API key to run the script.
The data for the images is from when I started saving the data up to 2024. 

One image in the repository shows the mean deviations of the minimum temperature. 
Clearly the long-term forecast is to be taken with a grain of salt. Not that there is anything better, nor are these values ever equal for the whole of the Netherlands (but taking the mean should be an advantage in the precision of the forecast right?). Forecast and prediction is used here with the same intent (forecast).
