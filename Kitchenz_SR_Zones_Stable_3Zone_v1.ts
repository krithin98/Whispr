#// Kitchenz S/R Zones – Stable 3-Zone Minimal Version
#// ThinkScript for ThinkorSwim
#// Features: Manual pivot detection, 3 persistent S/R zones, safe plotting, debugging labels

input pivotLength = 3;
input showLabels = yes;

def bar = BarNumber();

def isPivotHigh = if bar > pivotLength and high[pivotLength] == Highest(high, pivotLength * 2 + 1) then 1 else 0;
def isPivotLow  = if bar > pivotLength and low[pivotLength]  == Lowest(low, pivotLength * 2 + 1) then 1 else 0;

// Store the most recent pivot high/low
def lastPivotHigh = CompoundValue(1, if isPivotHigh then high[pivotLength] else lastPivotHigh[1], Double.NaN);
def lastPivotLow  = CompoundValue(1, if isPivotLow  then low[pivotLength]  else lastPivotLow[1],  Double.NaN);

// Plot a cloud between the most recent high and low
AddCloud(lastPivotHigh, lastPivotLow, Color.LIGHT_RED, Color.LIGHT_GREEN);

AddLabel(showLabels, "Last Pivot High: " + lastPivotHigh, Color.RED);
AddLabel(showLabels, "Last Pivot Low: " + lastPivotLow, Color.GREEN);

def res1 = CompoundValue(1, if isPivotHigh then high[pivotLength] else res1[1], high);
def res2 = CompoundValue(1, if isPivotHigh and high[pivotLength] < res1[1] then high[pivotLength] else res2[1], high);
def res3 = CompoundValue(1, if isPivotHigh and high[pivotLength] < res2[1] then high[pivotLength] else res3[1], high);

def sup1 = CompoundValue(1, if isPivotLow then low[pivotLength] else sup1[1], low);
def sup2 = CompoundValue(1, if isPivotLow and low[pivotLength] > sup1[1] then low[pivotLength] else sup2[1], low);
def sup3 = CompoundValue(1, if isPivotLow and low[pivotLength] > sup2[1] then low[pivotLength] else sup3[1], low);

AddCloud(res1, res2, Color.RED, Color.RED, yes);
AddCloud(res2, res3, Color.PINK, Color.PINK, yes);
AddCloud(sup1, sup2, Color.GREEN, Color.GREEN, yes);
AddCloud(sup2, sup3, Color.LIGHT_GREEN, Color.LIGHT_GREEN, yes);

AddLabel(showLabels, "Res1: " + res1 + " | Res2: " + res2 + " | Res3: " + res3, Color.RED);
AddLabel(showLabels, "Sup1: " + sup1 + " | Sup2: " + sup2 + " | Sup3: " + sup3, Color.GREEN);
AddLabel(showLabels, "PivotHigh: " + isPivotHigh + " | PivotLow: " + isPivotLow, Color.YELLOW); 