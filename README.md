# Census Dashboard

// TODO


# UX Improvements

## 1. Overall UI Flow
1. **Group related controls together:**  
   - The user needs to do three things most frequently:  
     (a) Select or search for table codes.  
     (b) Add or remove map points of interest.  
     (c) Set a radius and request data.  
   - You could place these related inputs in a card or a well-organized side panel so that everything needed to run the analysis is in one place.
2. **Provide hints or an onboarding prompt:**  
   - If a user lands on the app for the first time, guide them through the steps: “1. Search or enter table codes. 2. Click on the map to add points. 3. Adjust the radius. 4. Click ‘Get Data.’”  
   - A short, condensed step-by-step tutorial or a collapsible help panel can improve the first-run experience.

---

## 2. Search & Table Codes
1. **Clarify usage of table-input:**  
   - Currently, users must enter comma-separated table codes. Let users click on search results to add them to the “table-input” automatically.

---

## 3. Points of Interest (POI) Management
1. **Map + Points Panel:**  
   - Users may not notice that they must first click on the map before pressing “Add Point.” Consider a step or an inline message near the “Add Point” button stating: “Click on the map to select a location, then click ‘Add Point.’”  
   - Or, if feasible, automatically add the point at the last clicked location—disable the button until the map has been clicked.
2. **Edit / rename points**:  
   - If a user wants to rename or update a point already on the map, right now they can only remove the last point or add new. Consider offering an in-place edit or a small list that shows all created points with the ability to rename or remove each.

---

## 4. Radius Slider & Distance
1. **Better radius input flexibility:**  
   - The slider works fine for casual adjustments, but you might also allow a direct numeric input box to handle larger ranges or more precise distances.  
2. **Unit toggle (miles vs. kilometers):**  
   - Depending on the user base, a toggle could help international audiences or certain use cases wanting metric units.

---

## 5. Map Interactions & Visual Elements
1. **Map legend or color coding:**  
   - When block groups are highlighted with varying opacity (`fillOpacity=overlap`), it can be unclear how that overlaps with “data coverage.” Consider using a color ramp to show the degree of overlap or a legend explaining how color/opacity relates to coverage.  
2. **Control panel vs. floating panel:**  
   - Many map apps have a collapsible side panel. Putting the main controls in a collapsible sidebar can leave the map front-and-center. This is especially helpful for smaller screens.

---

## 6. Get Data & Data Presentation
1. **Integrate “Get Data” with input:**  
   - Because “Get Data” is the final step, the button might be near or combined with table input, or at least in a more prominent position.  
   - Keep the explicit button but provide clear guidance on what it does.
2. **Data table clarity:**  
   - The resulting data is displayed in a pivoted table. Consider including a summary row or a short textual description of what the data is (e.g., “Population estimates for My Point, aggregated from block groups.”). 

---

## 7. Download Flow
1. **Confirm the data to be downloaded:**  
   - Show a short summary (“You’re about to download data for 2 points using table codes B01001, B01002”).  
   - A user can then verify they have the correct data before downloading.

---

## 8. Responsiveness & Visual Hierarchy
1. **Clear visual grouping:**  
   - Give each functional group (Search, Tables, Map + Points, Results) its own heading or card. Additional spacing or separators (e.g., a card around the “Add/Remove Point” section) can make the app look more polished.

---

## 9. Accessibility & Usability
1. **Labels & placeholders:**  
   - Ensure every input (`dbc.Input`, `dcc.Slider`) has clear labels. The existing placeholders help, but explicit labels that remain visible are beneficial for screen readers.  
   - Include a descriptive `aria-label` or `title` attribute for interactive elements, such as the “Add Point” button or the map.

---

## 10. Next-Level Enhancements
1. **Multiple radius support per point:**  
   - Some users might want to see multiple buffers (e.g., 1 mile, 3 miles, 5 miles) around the same point to compare coverage. Consider giving each point a custom radius.

---

## Conclusion

These recommendations aim to make the app more learnable and user-friendly. The biggest wins usually come from:

1. **Clear guidance** on how to use the app.  
2. **Fewer steps** and friction in core tasks (like searching for codes, adding points, and generating data).  
3. **Better visual hierarchy** and groupings so people can quickly locate relevant controls.  
4. **More intuitive map interactions** (hover highlights, color-coding, straightforward layering).

By iterating on these points, you’ll give users a smoother experience, reduce confusion, and help them get to the data they need faster and more confidently.