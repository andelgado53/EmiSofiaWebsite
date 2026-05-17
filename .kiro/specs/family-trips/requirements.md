# Requirements Document

## Introduction

"Family Trips" is a section of the personal website emisofia.com where the author documents family trips with photos and descriptions. Each trip entry contains a title, date, optional description, and a gallery of up to 20 photos. Visitors can browse all trips, view a trip's photo gallery in a grid layout, and click any photo to open a lightbox overlay that displays the photo at a larger size with navigation between photos — all without leaving the page. The author manages trips through the existing CMS (same JWT authentication) and uploads photos via presigned S3 URLs served through CloudFront, following the same infrastructure pattern as "Notes for Emi."

## Glossary

- **Website**: The personal website at emisofia.com containing all sections including "Family Trips."
- **Trip**: A record representing a single family trip, containing a title, date, optional description, and zero to 20 photos.
- **Author**: The father who creates and manages trip entries via the CMS.
- **Visitor**: Any person browsing the public website, including Emi.
- **Trip_List**: The public view that displays all published trips ordered from newest to oldest.
- **Trip_Detail**: The public view that displays a single trip's full content and photo gallery.
- **Photo_Gallery**: A grid layout within the Trip_Detail that displays all photos attached to a trip.
- **Lightbox**: A modal overlay that displays a single photo at a larger size on top of the current page, with controls to navigate between photos and close the overlay.
- **Cover_Photo**: The first photo in a trip's gallery, used as the thumbnail on the Trip_List.
- **CMS**: The existing Content Management System at /cms, protected by JWT authentication.
- **Storage**: The backend service responsible for persisting trip data and photo metadata.

---

## Requirements

### Requirement 1: Display Family Trips Section

**User Story:** As a visitor, I want to see a "Family Trips" section on the website, so that I can browse and view photos from the family's trips.

#### Acceptance Criteria

1. THE Website SHALL include a "Family Trips" section accessible via a clickable card on the homepage.
2. WHEN a visitor navigates to the "Family Trips" section, THE Trip_List SHALL display all published trips ordered by trip date from newest to oldest.
3. WHEN two trips share the same trip date, THE Trip_List SHALL order them by creation time, newest first.
4. WHEN the Trip_List contains no published trips, THE Trip_List SHALL display a message indicating that no trips are available yet.
5. WHEN the Trip_List is displayed, THE Trip_List SHALL show each trip's title, trip date, and Cover_Photo as a thumbnail.
6. WHEN a trip has no photos, THE Trip_List SHALL display a placeholder image in place of the Cover_Photo.
7. WHEN a visitor selects a trip from the Trip_List, THE Trip_Detail SHALL display the trip's title, trip date, description (if present), and Photo_Gallery.

---

### Requirement 2: Trip Content

**User Story:** As the Author, I want to create trip entries with a title, date, description, and photos, so that I can document family trips for Emi to look back on.

#### Acceptance Criteria

1. THE Trip SHALL contain a title of 1 to 150 characters, a trip date, an optional description of 0 to 2000 characters, and zero to 20 photos.
2. THE Trip SHALL have a status of either "draft" or "published."
3. WHEN the Trip_Detail is displayed and the trip has a description, THE Trip_Detail SHALL render the description preserving paragraph breaks.
4. IF the Author attempts to save a Trip with a title exceeding 150 characters, THEN THE CMS SHALL reject the save and display an error message indicating the character limit has been exceeded.
5. IF the Author attempts to save a Trip with a description exceeding 2000 characters, THEN THE CMS SHALL reject the save and display an error message indicating the character limit has been exceeded.

---

### Requirement 3: Trip Photo Gallery

**User Story:** As a visitor, I want to see all photos from a trip displayed in a grid layout, so that I can quickly browse the visual memories from that trip.

#### Acceptance Criteria

1. WHEN the Trip_Detail is displayed, THE Photo_Gallery SHALL render all attached photos in a responsive grid layout.
2. THE Photo_Gallery SHALL display photos in the order they were arranged by the Author (by position value, ascending).
3. WHEN the browser viewport is 768 pixels wide or wider, THE Photo_Gallery SHALL display photos in a grid of 3 or more columns.
4. WHEN the browser viewport is narrower than 768 pixels, THE Photo_Gallery SHALL display photos in a grid of 2 columns.
5. THE Photo_Gallery SHALL display each photo as a square thumbnail (cropped to fill) to maintain a uniform grid appearance.

---

### Requirement 4: Photo Lightbox

**User Story:** As a visitor, I want to click on a photo and see it enlarged without leaving the page, so that I can view the full detail of each photo easily.

#### Acceptance Criteria

1. WHEN a visitor clicks a photo in the Photo_Gallery, THE Lightbox SHALL open as a modal overlay displaying the selected photo at a larger size.
2. THE Lightbox SHALL NOT navigate the visitor to a different page.
3. WHILE the Lightbox is open, THE Lightbox SHALL display a "next" control and a "previous" control to navigate between photos in the trip.
4. WHEN the visitor activates the "next" control, THE Lightbox SHALL display the next photo in position order; WHEN the current photo is the last in the gallery, THE "next" control SHALL wrap to the first photo.
5. WHEN the visitor activates the "previous" control, THE Lightbox SHALL display the previous photo in position order; WHEN the current photo is the first in the gallery, THE "previous" control SHALL wrap to the last photo.
6. WHILE the Lightbox is open, THE Lightbox SHALL display a "close" control that closes the overlay and returns the visitor to the Photo_Gallery view.
7. WHEN the visitor presses the Escape key while the Lightbox is open, THE Lightbox SHALL close.
8. WHEN the visitor presses the right arrow key while the Lightbox is open, THE Lightbox SHALL display the next photo.
9. WHEN the visitor presses the left arrow key while the Lightbox is open, THE Lightbox SHALL display the previous photo.
10. WHILE the Lightbox is open, THE Lightbox SHALL display a dark semi-transparent backdrop behind the photo to focus attention on the image.

---

### Requirement 5: Trip Photo Management (CMS)

**User Story:** As the Author, I want to upload and manage photos for each trip, so that I can build a gallery of up to 20 photos per trip.

#### Acceptance Criteria

1. THE CMS SHALL allow the Author to upload a minimum of zero and a maximum of 20 photos per trip.
2. WHEN the Author uploads a photo, THE CMS SHALL accept only JPEG and PNG image files up to 10 MB each.
3. IF the Author attempts to upload more than 20 photos to a single trip, THEN THE CMS SHALL reject the additional photo and display a message stating that a maximum of 20 photos is allowed per trip.
4. IF an uploaded photo file exceeds 10 MB, THEN THE CMS SHALL reject the file and display a message stating the 10 MB per-file size limit.
5. IF the Author attempts to upload a file that is not a JPEG or PNG, THEN THE CMS SHALL reject the file and display a message stating that only JPEG and PNG files are accepted.
6. THE CMS SHALL allow the Author to reorder photos within a trip by dragging and dropping them into the desired position; THE CMS SHALL update position values automatically based on the new visual order.
7. THE CMS SHALL allow the Author to remove a photo from a trip.
8. WHEN the Author removes a photo from a trip, THE Storage SHALL delete the photo from S3 and remove the photo record from the database.
9. THE CMS SHALL upload photos via presigned S3 URLs and serve them through CloudFront, following the same pattern as "Notes for Emi" photo uploads.

---

### Requirement 6: Trip Authoring and Publishing

**User Story:** As the Author, I want to create, edit, publish, and delete trips, so that I can manage the Family Trips section content over time.

#### Acceptance Criteria

1. THE CMS SHALL provide a form where the Author can enter a title (up to 150 characters), a trip date, an optional description (up to 2000 characters), and upload up to 20 photos for a new trip.
2. THE CMS SHALL allow the Author to save a trip as a draft before publishing it.
3. IF the Author attempts to publish a trip with an empty title, THEN THE CMS SHALL reject the action and display an error message requiring a title.
4. IF the Author attempts to publish a trip without a trip date, THEN THE CMS SHALL reject the action and display an error message requiring a trip date.
5. WHEN the Author publishes a trip, THE Storage SHALL persist the trip and THE Trip_List SHALL include the new trip within 60 seconds.
6. THE CMS SHALL allow the Author to edit a previously published trip (title, date, description, and photos).
7. WHEN the Author edits and republishes a trip, THE Trip_Detail SHALL reflect the updated content within 60 seconds.
8. THE CMS SHALL allow the Author to delete a trip.
9. WHEN the Author deletes a trip, THE Trip_List SHALL no longer display the deleted trip within 60 seconds; THE Storage SHALL delete all associated photos from S3.
10. THE CMS SHALL be accessible only to the Author via the existing JWT authentication mechanism.

---

### Requirement 7: Infrastructure and Performance

**User Story:** As the Author, I want the Family Trips section to use the same infrastructure as the rest of the website, so that I do not need to manage additional services.

#### Acceptance Criteria

1. THE Website SHALL serve the Family Trips section over HTTPS at emisofia.com/trips.
2. THE Website SHALL serve trip photos via AWS CloudFront (CDN) for fast delivery.
3. THE Storage SHALL use AWS S3 to persist trip photos durably, with no data loss under normal operating conditions.
4. THE Storage SHALL use the existing SQLite database to persist trip metadata (title, date, description, photo records).
5. WHEN a visitor loads the Trip_List page, THE Website SHALL return the page within 3 seconds under normal network conditions.
6. WHEN a visitor loads the Trip_Detail page, THE Website SHALL return the page within 3 seconds under normal network conditions.
7. THE Family Trips backend endpoints SHALL be part of the existing FastAPI application.
8. THE Family Trips frontend pages SHALL be part of the existing Next.js application.
