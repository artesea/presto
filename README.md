# presto
My Pimoroni Presto examples

## [Agile Price Chart](https://github.com/artesea/presto/blob/main/agile-price-chart.py)

This will display the current pricing chart for the Octopus Energy Agile Tariff.

It also examples the touch screen and speaker by tweaking the backlight if you touch the left or right hand side whilst beeping.

The display will turn off between 11pm and 6am, but will come back on for 30 seconds if touched.

The rear LEDs will light up red during high prices.

You can tweak the thresholds for each colour within the code.

You may also wish to update the Agile API call to use the correct region, mine is the East Midlands (B). You can find the URL needs on the [API Access](https://octopus.energy/dashboard/new/accounts/personal-details/api-access) page within your Octopus account.
