# Google Trends Scaling and Alignment

Google Trends scores are relative search-interest indices, not absolute search
volumes. A maximum observed search term is usually assigned 100 within one export.

- Batch 1 terms: Dhurandhar, Chhaava, Coolie, Good Bad Ugly.
- Batch 2 terms: Su From So, Ekka, L2: Empuraan, Lokah Chapter 1: Chandra,
  Dhurandhar.
- The overlapping Dhurandhar series is the only cross-batch anchor.
- Both monthly exports were outer-aligned by the `Time` date and duplicate dates
  were removed. Missing values were preserved and never converted to zero.
- Monthly Dhurandhar matches exactly across the overlapping dates: `True`.
- Median overlap-based scale factor: `1`.
- Batch 1 remains on its original scale. Batch 2 values are multiplied by the
  median anchor ratio only if the original anchor series differs. Non-anchor
  Batch 2 values are also treated as estimates on the Batch 1 scale.
- Dhurandhar itself is taken from Batch 1 in the combined dataset to avoid
  duplicating or modifying its verified overlap values.
- Regional scores were not cross-batch aligned or combined. Dhurandhar's
  regional anchors differ between batches, so Batch 1 and Batch 2 regional
  data are kept and analysed separately.
- Combined figures should be interpreted as normalized comparative indices,
  not actual search counts or causal measures of audience demand.
