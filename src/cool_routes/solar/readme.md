# Shadow Modeling Approach

## Overview

The current implementation of the shadow model uses a simplified geometric approximation to estimate building shadows over the urban environment.

Instead of performing full 3D ray tracing or physically-based solar simulations, the model projects building footprints in the opposite direction of the solar azimuth using the estimated shadow length derived from building height and solar elevation.

This approach was intentionally selected as an initial approximation to support thermal-aware pedestrian routing at urban scale.

---

# Current Methodology

For each building polygon:

1. Solar altitude and azimuth are computed using `PySolar`
2. Shadow length is estimated as:

```text
shadow_length = building_height / tan(solar_altitude)
```
3. The building geometry is translated spatially according to:
* solar azimuth
* estimated shadow length

The resulting translated geometry is treated as an approximate shadow footprint.

---

# Important Limitation

The current implementation does not generate a physically exact shadow polygon.  

Specifically:  

* the original building footprint is translated
* the projected geometry represents an approximation of the shadow location
* the area between the original and projected geometry is not explicitly modeled  

Therefore, this method should be interpreted as:  

* a spatial proxy for urban shading
* a simplified shadow footprint approximation
* not a radiative or physically exact simulation
--- 
# Why This Approximation Was Chosen

The project focuses on:

* pedestrian thermal routing
* relative thermal comfort between street segments
* scalable urban analysis

rather than:  

* high-precision architectural shadow simulation
* photorealistic solar modeling
* energy simulation

The simplified approach provides several advantages:  

* computational efficiency
* scalability to large urban areas
* temporal flexibility (dynamic time-based shadows)
* low implementation complexity
* compatibility with graph-based routing workflows

For the current project stage, relative shadow coverage over street segments is more important than centimeter-level geometric precision.

# Intended Use

The shadow model is currently intended for:

* estimating shaded street segments
* computing shadow ratios over pedestrian edges
* integrating dynamic shading into thermal routing costs
* comparative urban comfort analysis

The outputs should not be interpreted as:

* exact solar exposure
* engineering-grade shadow simulations
* architectural daylight studies
* Future Improvements

Potential future upgrades include:

* full shadow polygon extrusion
* 3D urban geometry
* ray tracing methods
* raster-based shadow casting
* vegetation/canopy shadow integration
* terrain-aware shadow modeling

However, these improvements are currently outside the scope of the MVP and early research phase.
---

# Design Philosophy

The current implementation prioritizes:

* reproducibility
* interpretability
* computational tractability
* urban-scale applicability

over physical realism.

This trade-off is considered acceptable for the current routing and thermal comfort objectives of the project.