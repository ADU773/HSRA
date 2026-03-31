```markdown
# Design System Strategy: The Atmospheric Interface

## 1. Overview & Creative North Star
The Creative North Star for this design system is **"The Digital Laboratory."** 

Unlike standard dashboards that feel like rigid spreadsheets, this system treats data as a living, breathing element housed within a high-end, light-filled environment. We move beyond the "template" look by embracing **High-Chroma Whites** and **Tonal Depth**. The goal is to create a professional AI workspace that feels as precise as a scientific instrument but as airy as a contemporary art gallery. 

By utilizing intentional asymmetry and overlapping surface layers, we create a sense of architectural "flow" rather than a boxed-in grid. We prioritize the "Light Level" aesthetic—a high-exposure, low-contrast environment that reduces cognitive load for technical users.

---

## 2. Colors & Surface Philosophy
The palette is rooted in a sophisticated range of cool grays (`surface`) and surgical teals (`primary`).

### The "No-Line" Rule
Traditional 1px solid borders are strictly prohibited for sectioning. To define a workspace, you must use **Background Color Shifts**. 
*   **Application:** Place a `surface-container-low` (#f0f4f7) sidebar against the main `background` (#f7f9fb). The boundary is felt through the shift in tone, not a drawn line.

### Surface Hierarchy & Nesting
Treat the UI as a series of physical layers of fine paper. 
*   **Base:** `background` (#f7f9fb)
*   **Sectioning:** `surface-container` (#eaeff2) for secondary layout blocks.
*   **Emphasis:** `surface-container-lowest` (#ffffff) for the primary interactive cards or data tables to make them "pop" against the gray base.

### The "Glass & Gradient" Rule
To elevate the "AI" technical feel, use Glassmorphism for floating overlays (like Command Palettes or Tooltips). 
*   **Execution:** Use `surface` (#f7f9fb) at 70% opacity with a `20px` backdrop-blur. 
*   **Signature Texture:** Main Action Buttons or Hero Data Points should use a subtle linear gradient: `primary` (#006978) to `primary_dim` (#005c69) at a 135° angle to provide a "lit-from-within" soul.

---

## 3. Typography: Editorial Precision
We utilize a dual-sans-serif approach to balance technical authority with modern approachable aesthetics.

*   **The Power Pair:** **Manrope** is used for `display` and `headline` tiers to provide a geometric, high-end editorial feel. **Inter** is used for `title`, `body`, and `label` tiers for its industry-leading legibility in data-heavy contexts.
*   **Scale Dynamics:** Use `display-md` (2.75rem) sparingly for key AI confidence scores or system status. Ensure `label-sm` (0.6875rem) is always in `on-surface-variant` (#596064) to provide a clear distinction between data and metadata.

---

## 4. Elevation & Depth
Depth is a function of light and stacking, never heavy shadows.

*   **The Layering Principle:** Instead of shadows, stack `surface-container-lowest` cards on `surface-container-low` backgrounds. This creates a "soft lift."
*   **Ambient Shadows:** If a component must float (e.g., a dropdown), use a shadow with a blur of `32px` at 6% opacity, using a tint of `on-surface` (#2c3437). It should look like a soft glow, not a dark smudge.
*   **The "Ghost Border" Fallback:** For input fields or essential containment, use the `outline-variant` (#acb3b7) at **15% opacity**. This creates a suggestion of a boundary that disappears into the "Light Level" aesthetic.

---

## 5. Components

### Buttons & Inputs
*   **Primary Button:** Gradient-filled (`primary` to `primary_dim`), `xl` roundedness (0.75rem). No border.
*   **Secondary/Tertiary:** `surface-container-highest` background with `primary` text. Use `md` roundedness (0.375rem).
*   **Input Fields:** Use `surface-container-lowest` (#ffffff) with a "Ghost Border." On focus, transition the border to `primary` (#006978) at 100% opacity.

### Data Visualization & Lists
*   **Cards:** Forbid divider lines. Separate content using `spacing-6` (1.5rem) or by nesting a `surface-container-high` block inside a `surface-container-lowest` card.
*   **Chips:** Use `secondary-container` (#d3e4fe) with `on-secondary-container` (#435368) text for status indicators. Use `full` (9999px) roundedness.
*   **The AI Pulse (Custom Component):** A small, soft-glowing teal dot using `primary-fixed` (#8debff) with a `10px` blur to indicate active AI processing/inference.

---

## 6. Do's and Don'ts

### Do:
*   **DO** use whitespace as a structural element. If in doubt, increase spacing by one tier on the scale.
*   **DO** use `surface-bright` for the most important data highlights to draw the eye without using high-contrast colors.
*   **DO** ensure all "High-End" layouts maintain a 40px (`10`) or 64px (`16`) outer margin to give the dashboard "breathing room."

### Don't:
*   **DON'T** use pure black (#000000). Use `on-surface` (#2c3437) for all primary text to maintain the soft, airy vibe.
*   **DON'T** use 1px solid borders to separate sidebar from content. Use a tonal shift from `surface-container-low` to `background`.
*   **DON'T** use standard "drop shadows." If it doesn't look like ambient light, it's too heavy for this system.
*   **DON'T** use "Dark Mode" logic. This system is designed to live in the light; darkening it will break the tonal hierarchy.

---

## 7. Scaling & Spacing
Always adhere to the **Soft-Grid**.
*   **Inner-component padding:** Use `2` (0.5rem) or `3` (0.75rem).
*   **Component-to-Component spacing:** Use `5` (1.25rem) or `8` (2rem).
*   **Section-to-Section spacing:** Use `12` (3rem) to define clear content boundaries without lines.