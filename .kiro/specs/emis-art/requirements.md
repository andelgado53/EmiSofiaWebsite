# Requirements Document

## Introduction

"Emi's Art" is a section of the personal website emisofia.com where the author showcases art pictures created by Emi, grouped by year. Unlike "Family Trips" which organizes content by individual trip events, art pictures are simply grouped by the year they were created. Each year contains a gallery of art pictures, and each art piece may have an optional title or caption. Visitors can browse art by year, view the gallery for a given year, and use a lightbox to see individual pieces at full size. The author manages art through the existing CMS (same JWT authentication) and uploads photos via presigned S3 URLs served through CloudFront, following the same infrastructure pattern as the rest of the website. The homepage and navigation bar already have placeholder elements for "Emi's Art" that need to be activated.

## Glossary

- **Website**: The personal website at emisofia.com containing all sections including "Emi's Art."
- **Art_Piece**: A single art picture uploaded by the Author, containing an image, an optional title/caption, and a position within its year.
- **Year_Group**: A logical grouping of art pieces by the year they were created (e.g., 2025, 2024).
- **Year_List**: The public view that displays all years containing published art, ordered from newest to oldest.
- **Year_Gallery**: The public view that displays all art pieces for a selected year in a grid layout.
- **Lightbox**: A modal overlay that displays a single art piece at a larger size on top of the current page, with controls to navigate between pieces and close the overlay.
- **Cover_Piece**: The first art piece (position 1) in a Year_Group, used as the thumbnail on the Year_List.
- **Author**: The father who creates and manages art entries via the CMS.
- **Visitor**: Any person browsing the public website, including Emi.
- **CMS**: The existing Content Management System at /cms, protected by JWT authentication.
- **Storage**: The backend service responsible for persisting art data and photo metadata.

---

## Requirements

### Requirement 1: Display Emi's Art Section

**User Story:** As a visitor, I want to see an "Emi's Art" section on the website, so that I can browse and view Emi's art pictures organized by year.

#### Acceptance Criteria

1. THE Website SHALL include an "Emi's Art" section accessible via a clickable card on the homepage.
2. THE Website SHALL include an "Emi's Art" link in the navigation bar that navigates to the art section.
3. WHEN a visitor navigates to the "Emi's Art" section, THE Year_List SHALL display all years that contain at least one published Art_Piece, ordered from newest year to oldest year.
4. WHEN the Year_List contains no years with published art, THE Year_List SHALL display a message indicating that no art is available yet.
5. WHEN the Year_List is displayed, THE Year_List SHALL show each Year_Group's year number and the Cover_Piece as a thumbnail, where the Cover_Piece is the published Art_Piece with the lowest position value in that Year_Group.
6. WHEN a Year_Group has no published art pieces, THE Year_List SHALL NOT display that Year_Group.
7. WHEN a visitor selects a year from the Year_List, THE Year_Gallery SHALL display all published art pieces for that year ordered by position value ascending.
8. IF a visitor navigates to a Year_Gallery and no published art pieces exist for that year, THEN THE Year_Gallery SHALL display a message indicating that no art is available for the selected year and provide a link back to the Year_List.

---

### Requirement 2: Art Piece Content

**User Story:** As the Author, I want to upload art pieces with an optional title/caption, so that I can showcase Emi's artwork with context when needed.

#### Acceptance Criteria

1. THE Art_Piece SHALL contain an image, a year (four-digit integer between 2020 and the current calendar year, inclusive), an optional title/caption of 0 to 200 characters, and a position (integer starting at 1) within its Year_Group.
2. THE Art_Piece SHALL have a status of either "draft" or "published," defaulting to "draft" when first created.
3. WHEN the Year_Gallery displays an Art_Piece that has a title, THE Year_Gallery SHALL render the title below the art image.
4. WHEN the Year_Gallery displays an Art_Piece that has no title, THE Year_Gallery SHALL display the image without a title caption.
5. IF the Author attempts to save an Art_Piece with a title exceeding 200 characters, THEN THE CMS SHALL reject the save and display an error message indicating the character limit has been exceeded.
6. IF the Author attempts to save an Art_Piece with a year outside the range 2020 to the current calendar year, THEN THE CMS SHALL reject the save and display an error message indicating the valid year range.

---

### Requirement 3: Art Year Gallery

**User Story:** As a visitor, I want to see all art pieces from a given year displayed in a grid layout, so that I can browse Emi's artwork for that year.

#### Acceptance Criteria

1. WHEN the Year_Gallery is displayed, THE Year_Gallery SHALL render all published art pieces for the selected year in a responsive grid layout.
2. THE Year_Gallery SHALL display art pieces in the order arranged by the Author (by position value, ascending).
3. WHEN the browser viewport is 768 pixels wide or wider, THE Year_Gallery SHALL display art pieces in a grid of 3 or more columns.
4. WHEN the browser viewport is narrower than 768 pixels, THE Year_Gallery SHALL display art pieces in a grid of 2 columns.
5. THE Year_Gallery SHALL display each art piece as a square thumbnail (cropped to fill) to maintain a uniform grid appearance.
6. THE Year_Gallery SHALL display the four-digit year number as a heading above the grid.
7. IF the selected year contains zero published art pieces, THEN THE Year_Gallery SHALL display a message indicating that no art is available for that year.
8. THE Year_Gallery SHALL provide a navigation link that returns the visitor to the Year_List.

---

### Requirement 4: Art Lightbox

**User Story:** As a visitor, I want to click on an art piece and see it enlarged without leaving the page, so that I can view the full detail of each piece easily.

#### Acceptance Criteria

1. WHEN a visitor clicks an art piece in the Year_Gallery, THE Lightbox SHALL open as a modal overlay displaying the selected art piece scaled to fit within the viewport while maintaining its aspect ratio, with at least 5% padding from the viewport edges.
2. THE Lightbox SHALL NOT navigate the visitor to a different page.
3. WHILE the Lightbox is open and the Year_Group contains more than one art piece, THE Lightbox SHALL display a "next" control and a "previous" control to navigate between art pieces in the year; WHILE the Year_Group contains exactly one art piece, THE Lightbox SHALL NOT display navigation controls.
4. WHEN the visitor activates the "next" control, THE Lightbox SHALL display the next art piece in position order; WHEN the current piece is the last in the gallery, THE "next" control SHALL wrap to the first piece.
5. WHEN the visitor activates the "previous" control, THE Lightbox SHALL display the previous art piece in position order; WHEN the current piece is the first in the gallery, THE "previous" control SHALL wrap to the last piece.
6. WHILE the Lightbox is open, THE Lightbox SHALL display a "close" control that closes the overlay and returns the visitor to the Year_Gallery view.
7. WHEN the visitor presses the Escape key while the Lightbox is open, THE Lightbox SHALL close.
8. WHEN the visitor presses the right arrow key while the Lightbox is open, THE Lightbox SHALL display the next art piece.
9. WHEN the visitor presses the left arrow key while the Lightbox is open, THE Lightbox SHALL display the previous art piece.
10. WHILE the Lightbox is open, THE Lightbox SHALL display a backdrop with 70% opacity behind the art piece, covering the entire viewport.
11. WHILE the Lightbox is open and the displayed Art_Piece has a title, THE Lightbox SHALL display the title below the image.
12. WHEN the visitor clicks the backdrop area outside the art piece and controls, THE Lightbox SHALL close.
13. WHILE the Lightbox is open, THE Lightbox SHALL trap keyboard focus within the overlay so that Tab and Shift+Tab cycle only through the Lightbox controls, and THE Lightbox SHALL apply an aria-modal attribute to indicate modal state to assistive technologies.

---

### Requirement 5: Art Piece Management (CMS)

**User Story:** As the Author, I want to upload and manage art pieces for each year, so that I can build a gallery of Emi's artwork over time.

#### Acceptance Criteria

1. THE CMS SHALL allow the Author to upload art pieces and assign each piece to a specific year (four-digit integer between 2020 and the current calendar year, inclusive).
2. WHEN the Author uploads an art piece, THE CMS SHALL accept only JPEG and PNG image files up to 10 MB each.
3. IF the Author attempts to upload a file that exceeds 10 MB, THEN THE CMS SHALL reject the file and display a message stating the 10 MB per-file size limit.
4. IF the Author attempts to upload a file that is not a JPEG or PNG, THEN THE CMS SHALL reject the file and display a message stating that only JPEG and PNG files are accepted.
5. THE CMS SHALL allow the Author to reorder art pieces within a year by dragging and dropping them into the desired position; THE CMS SHALL update position values automatically based on the new visual order.
6. THE CMS SHALL allow the Author to remove an art piece after the Author confirms the removal via a confirmation prompt.
7. WHEN the Author confirms removal of an art piece, THE Storage SHALL delete the image from S3, remove the art piece record from the database, and re-sequence the position values of the remaining art pieces in that year so that positions remain contiguous starting from 1.
8. THE CMS SHALL upload art images via presigned S3 URLs and serve them through CloudFront, following the same pattern as other photo uploads on the website.
9. THE CMS SHALL allow the Author to set or edit the optional title/caption for each art piece.
10. IF the presigned URL generation or the S3 image upload fails, THEN THE CMS SHALL display an error message indicating the upload could not be completed and SHALL NOT create an art piece record in the database.

---

### Requirement 6: Art Publishing and Lifecycle

**User Story:** As the Author, I want to create, publish, and delete art pieces, so that I can manage the Emi's Art section content over time.

#### Acceptance Criteria

1. THE CMS SHALL provide a form where the Author can select a year (four-digit integer, between 2020 and the current year inclusive), upload an image, and optionally enter a title/caption (0 to 200 characters) for a new art piece.
2. WHEN the Author saves a new art piece, THE CMS SHALL persist the art piece with a status of "draft" and assign it the next available position (appended after the last existing piece) within the selected year.
3. WHEN the Author publishes an art piece, THE Storage SHALL update the art piece status to "published" and THE Year_Gallery for that year SHALL include the new piece within 60 seconds.
4. IF the Author attempts to publish an art piece that has no uploaded image, THEN THE CMS SHALL reject the publish action and display an error message indicating that an image is required.
5. THE CMS SHALL allow the Author to edit a previously published art piece's title/caption (0 to 200 characters).
6. WHEN the Author edits and saves a published art piece, THE Year_Gallery SHALL reflect the updated content within 60 seconds.
7. THE CMS SHALL allow the Author to delete an art piece by presenting a confirmation prompt before executing the deletion.
8. WHEN the Author confirms deletion of an art piece, THE Year_Gallery SHALL no longer display the deleted piece within 60 seconds and THE Storage SHALL delete the associated image from S3.
9. IF an unauthenticated user attempts to access any CMS art management endpoint, THEN THE CMS SHALL reject the request and return an authentication error without exposing art data.
10. THE CMS SHALL display art pieces grouped by year in the management view, showing both draft and published pieces, allowing the Author to manage pieces within each year.

---

### Requirement 7: Homepage and Navigation Activation

**User Story:** As the Author, I want the existing placeholder elements for "Emi's Art" to become active links, so that visitors can navigate to the art section.

#### Acceptance Criteria

1. THE Website homepage SHALL display the "Emi's Art" card as a clickable link navigating to /art, using the violet color scheme (violet border and violet background) with hover states (darkened border and shadow on hover) consistent with the other active section cards.
2. THE Website navigation bar SHALL display the "Emi's Art" link as a clickable link navigating to /art, styled with violet text color and hover background consistent with how other navigation links use their respective section colors.
3. THE "Emi's Art" card on the homepage SHALL display a descriptive subtitle text and use active text colors (not grayed out), matching the text treatment of the other section cards.

---

### Requirement 8: Infrastructure and Performance

**User Story:** As the Author, I want the Emi's Art section to use the same infrastructure as the rest of the website, so that I do not need to manage additional services.

#### Acceptance Criteria

1. THE Website SHALL serve the Emi's Art section over HTTPS at emisofia.com/art.
2. THE Website SHALL serve art images via the same AWS CloudFront distribution used by other photo sections on the website.
3. THE Storage SHALL use the same AWS S3 bucket used by other photo sections to persist art images, with S3's standard durability guarantees.
4. THE Storage SHALL use the existing SQLite database to persist art piece metadata (year, title, position, image references) alongside existing tables.
5. WHEN a visitor loads the Year_List page, THE Website SHALL return the fully rendered HTML (excluding lazy-loaded images) within 3 seconds, measured from request initiation to document-complete on a connection with at least 5 Mbps bandwidth and under 100 ms latency.
6. WHEN a visitor loads the Year_Gallery page, THE Website SHALL return the fully rendered HTML (excluding lazy-loaded images) within 3 seconds, measured from request initiation to document-complete on a connection with at least 5 Mbps bandwidth and under 100 ms latency.
7. THE Emi's Art backend endpoints SHALL be part of the existing FastAPI application, sharing the same process and configuration.
8. THE Emi's Art frontend pages SHALL be part of the existing Next.js application, sharing the same build and deployment pipeline.
9. IF AWS S3 or CloudFront is unreachable when a visitor loads the Year_Gallery, THEN THE Website SHALL display the page layout with placeholder indicators where images would appear, without returning an error page.
