# ChartAreaInteractive Component

## Overview
A highly configurable, interactive analytics chart component that displays time-series data with multiple metric types, categories, and view modes.

## Features

### 1. Multiple Metric Types
- **Revenue**: Dollar amounts from upsells, upsizes, and add-ons
- **Opportunities**: Count of potential upsell/upsize/add-on opportunities
- **Offers**: Count of times operators offered upsells/upsizes/add-ons
- **Successes**: Count of successful conversions
- **Conversion Rate**: Percentage of offers that resulted in success (0-100%)

### 2. Category Filtering
- **Upsell**: Burger → Meal conversions
- **Upsize**: Size increase (Small → Medium → Large)
- **Add-ons**: Extra toppings/items

### 3. View Modes
- **Stacked**: Categories stack on top of each other (total sum visible)
- **Individual**: Categories overlay for comparison

### 4. Smart Scaling
- **Dynamic Y-axis**: Automatically scales based on data range
- **Top Padding**: 20% padding above max value prevents peak clipping
- **Bottom Padding**: 5% padding below min value (or 0) prevents bottom clipping
- **Conversion Rate Cap**: Automatically capped at 100%
- **Minimum Range**: Ensures minimum 10-unit range for visibility

### 5. Edge Case Handling

#### Data Edge Cases
✅ **Empty Data**: Shows "No analytics data available" message
✅ **Single Data Point**: Displays correctly with proper scaling
✅ **Zero Values**: Handles gracefully with minimum range
✅ **Very Small Values** (<10): Ensures minimum 10-unit range
✅ **Very Large Values**: Uses k-notation (e.g., $1.5k, 2.3k items)
✅ **All Zeros**: Displays 0-10 range for visibility
✅ **Negative Values**: Prevented by data structure (all metrics are positive)

#### UI Edge Cases
✅ **Conversion Rate Stacking**: NEVER stacks percentages (always individual)
✅ **Multiple Categories Selected**: Properly calculates combined domain
✅ **Single Category Selected**: Works correctly
✅ **Bottom Clipping**: 5px bottom margin + proper Y-axis domain
✅ **Top Clipping**: 20% padding + increased top margin (12px)
✅ **Tooltip Vibration**: All formatters memoized to prevent re-renders
✅ **Color-Coded Tooltips**: Colored dots match category colors
✅ **Mobile Responsive**: Adapts layout for small screens

#### Metric-Specific Behavior
- **Revenue (Stacked)**: Sum of all categories (correct)
- **Revenue (Individual)**: Compare categories side-by-side (correct)
- **Conversion Rate (Stacked)**: FORCES individual mode (percentages can't stack)
- **Conversion Rate (Individual)**: Overlay for comparison (correct)
- **Counts (Stacked)**: Sum totals (correct)
- **Counts (Individual)**: Compare counts (correct)

### 6. Performance Optimizations
- ✅ All formatters wrapped in `useCallback`
- ✅ Chart components memoized with `useMemo`
- ✅ Gradient definitions memoized
- ✅ Area components memoized
- ✅ Animations disabled on Area components to prevent jitter
- ✅ Tooltip animation controlled (200ms duration)

### 7. Accessibility
- ✅ ARIA labels on all controls
- ✅ Keyboard navigation support
- ✅ Semantic HTML
- ✅ Screen reader friendly
- ✅ `accessibilityLayer` enabled on chart

### 8. State Persistence
- **URL Parameters**: Chart state saved in URL for sharing
  - `?metric=revenue&categories=upsell,upsize&view=stacked&range=30d`
- **LocalStorage**: User preferences persist across sessions
- **Auto-Sync**: URL and localStorage stay synchronized

## Chart Dimensions

### Spacing & Margins
```tsx
Chart Height: 320px
Top Margin: 12px
Right Margin: 12px
Left Margin: 0px (handled by Y-axis width)
Bottom Margin: 5px

Y-axis Width:
  - Conversion Rate: 50px
  - Other Metrics: 60px
```

### Y-Axis Domain Calculation
```
For Stacked Mode (non-conversion-rate):
  - Min: 0 (always)
  - Max: sum(all_categories) * 1.2

For Individual Mode OR Conversion Rate:
  - Min: max(0, min_value - 5% of max)
  - Max: max_value * 1.2

For Conversion Rate specifically:
  - Min: 0 (always)
  - Max: min(calculated_max, 100)

Minimum Range: 10 units
```

## Color Scheme
- **Upsell**: `hsl(var(--chart-1))` - Primary color
- **Upsize**: `hsl(var(--chart-2))` - Secondary color
- **Add-ons**: `hsl(var(--chart-3))` - Tertiary color

## Usage Example

```tsx
<ChartAreaInteractive locationId="abc-123" />
```

## Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| locationId | string \| undefined | No | Location ID to fetch analytics for |

## Component Structure

```
components/chart-area-interactive/
├── index.tsx                    # Main chart component
├── MetricTypeSelector.tsx       # Dropdown for metric selection
├── CategoryFilter.tsx           # Category toggle/popover
├── ViewModeToggle.tsx          # Stacked vs Individual
├── ChartFilters.tsx            # Filter wrapper
├── useChartDataTransform.ts    # Data transformation hook
├── types.ts                    # Component types
└── README.md                   # This file
```

## Known Limitations

1. **Time Range**: Limited to 7d, 30d, 90d presets (custom date range not implemented)
2. **Worker Filtering**: Not implemented (shows all workers combined)
3. **Comparison Mode**: Current vs previous period comparison not implemented
4. **Export**: No CSV/PNG export functionality
5. **Max Data Points**: May have performance issues with >365 data points

## Future Enhancements

1. Custom date range picker
2. Worker-specific filtering
3. Comparison mode overlay
4. Export to CSV/PNG
5. Trend indicators (↑↓ arrows)
6. Highlight best/worst performing days
7. Summary statistics panel
8. Zoom/pan functionality for large datasets
