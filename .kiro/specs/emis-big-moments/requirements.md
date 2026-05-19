# Requirements Document

## Introduction

"Emi's Big Moments" is a section of the personal website emisofia.com where the author documents significant moments in Emi's life with a title, date, description, and up to 2 photos. Unlike the "Family Trips" section which features a full photo gallery and lightbox, this section is simpler: each moment displays its photos inline at full size in the detail view. Visitors can browse all moments ordered by date (newest first) and view individual moment details. The author manages moments through the existing CMS (same JWT authentication) and uploads photos via presigned S3 URLs served through CloudFront, following the same infrastructure pattern as the rest of the website.

## Glossary

- **Website**: The personal website at emisofia.com containing all sections including "Emi's Big Moments."
- **Moment**: A record representing a significant moment in Emi's life, containing a title, date, description, and zero to 2 photos.
- **Author**: The father who creates and manages moment entries via the CMS.
- **Visitor**: Any person browsing the public website, including Emi.
- **Moment_List**: The public view at /moments that displays all published moments ordered from newest to oldest by date.
- **Moment_Detail**: The public view at /moments/{id} that displays a single moment's full content and photos.
- **Cover_Photo**: The photo at position 1 attached to a moment, used as the thumbnail on the Moment_List.
- **CMS**: The existing Content Management System at /cms, protected by JWT authentication.
- **Storage**: The backend service responsible for persisting moment data and photo metadata.

---

## Requirements

### Requirement 1: Display Emi's Big Moments Section

**User Story:** As a visitor, I want to see an "Emi's Big Moments" section on the website, so that I can browse and view photos from significant moments in Emi's life.

#### Acceptance Criteria

1. THE Website SHALL include an "Emi's Big Moments" section accessible via a clickable card on the homepage.
2. THE Website SHALL include an "Emi's Big Moments" link in the navigation bar.
3. WHEN a visitor navigates to the "Emi's Big Moments" section, THE Moment_List SHALL display all published moments ordered by date from newest to oldest.
4. WHEN two moments share the same date, THE Moment_List SHALL order them by creation time, newest first.
5. WHEN the Moment_List contains no published moments, THE Moment_List SHALL display a message indicating that no moments are available yet.
6. WHEN the Moment_List is displayed, THE Moment_List SHALL show each moment's title, date, and Cover_Photo (the photo at position 1) as a thumbnail.
7. WHEN a moment has no photos, THE Moment_List SHALL display a placeholder image in place of the Cover_Photo.
8. WHEN a visitor selects a moment from the Moment_List, THE Moment_Detail SHALL display the moment's title, date, description, and photos.
9. IF a visitor navigates to a Moment_Detail URL with an ID that does not exist or is not published, THEN THE Website SHALL display a 404 page indicating the moment was not found.

---

### Requirement 2: Moment Content

**User Story:** As the Author, I want to create moment entries with a title, date, description, and photos, so that I can document significant moments for Emi to look back on.

#### Acceptance Criteria

1. THE Moment SHALL contain a title of 1 to 150 characters, a date, a description of 1 to 2000 characters, and zero to 2 photos.
2. THE Moment SHALL have a status of either "draft" or "published"; WHEN a new moment is created, THE Storage SHALL assign a default status of "draft."
3. WHEN the Moment_Detail is displayed and the moment has a description, THE Moment_Detail SHALL render the description preserving paragraph breaks (newline characters rendered as line breaks).
4. IF the Author attempts to save a Moment with a title shorter than 1 character or exceeding 150 characters, THEN THE CMS SHALL reject the save and display an error message indicating the title must be between 1 and 150 characters.
5. IF the Author attempts to save a Moment with a description shorter than 1 character or exceeding 2000 characters, THEN THE CMS SHALL reject the save and display an error message indicating the description must be between 1 and 2000 characters.

---

### Requirement 3: Moment Photo Display

**User Story:** As a visitor, I want to see the photos from a moment displayed inline at full size, so that I can view the images clearly without additional interaction.

#### Acceptance Criteria

1. WHEN the Moment_Detail is displayed and the moment has photos, THE Moment_Detail SHALL display each photo inline with a maximum width constrained to the content area width, maintaining the original aspect ratio.
2. THE Moment_Detail SHALL display photos in the order of their position value, ascending (position 1 first, position 2 second).
3. WHEN the moment has two photos, THE Moment_Detail SHALL display both photos stacked vertically with consistent spacing between them.
4. THE Moment_Detail SHALL NOT use a lightbox or modal overlay for photo viewing.

---

### Requirement 4: Moment Photo Management (CMS)

**User Story:** As the Author, I want to upload and manage photos for each moment, so that I can attach up to 2 photos per moment.

#### Acceptance Criteria

1. THE CMS SHALL allow the Author to upload a minimum of zero and a maximum of 2 photos per moment.
2. WHEN the Author uploads a photo, THE CMS SHALL accept only JPEG and PNG image files up to 10 MB each.
3. IF the Author attempts to upload more than 2 photos to a single moment, THEN THE CMS SHALL reject the additional photo and display a message stating that a maximum of 2 photos is allowed per moment.
4. IF an uploaded photo file exceeds 10 MB, THEN THE CMS SHALL reject the file and display a message stating the 10 MB per-file size limit.
5. IF the Author attempts to upload a file that is not a JPEG or PNG, THEN THE CMS SHALL reject the file and display a message stating that only JPEG and PNG files are accepted.
6. THE CMS SHALL allow the Author to reorder photos within a moment by dragging and dropping them into the desired position; THE CMS SHALL update position values automatically based on the new visual order.
7. THE CMS SHALL allow the Author to remove a photo from a moment.
8. WHEN the Author removes a photo from a moment, THE Storage SHALL delete the photo from S3, remove the photo record from the database, and re-sequence the remaining photos' position values starting from 1 with no gaps.
9. THE CMS SHALL upload photos via presigned S3 URLs and serve them through CloudFront, following the same pattern as existing photo uploads.

---

### Requirement 5: Moment Authoring and Publishing

**User Story:** As the Author, I want to create, edit, publish, and delete moments, so that I can manage the Emi's Big Moments section content over time.

#### Acceptance Criteria

1. THE CMS SHALL provide a form at /cms/moments/new where the Author can enter a title (1 to 150 characters), a date, a description (1 to 2000 characters), and upload up to 2 photos for a new moment.
2. THE CMS SHALL allow the Author to save a moment as a draft without publishing it.
3. IF the Author attempts to publish a moment with an empty title, THEN THE CMS SHALL reject the action and display an error message requiring a title of 1 to 150 characters.
4. IF the Author attempts to publish a moment without a date, THEN THE CMS SHALL reject the action and display an error message requiring a date.
5. IF the Author attempts to publish a moment without a description, THEN THE CMS SHALL reject the action and display an error message requiring a description of 1 to 2000 characters.
6. WHEN the Author publishes a moment, THE Storage SHALL persist the moment with status "published" and THE Moment_List SHALL include the new moment within 60 seconds.
7. THE CMS SHALL provide a list view at /cms/moments where the Author can see all moments (drafts and published) ordered by date, newest first.
8. THE CMS SHALL allow the Author to edit a previously published moment (title, date, description, and photos) at /cms/moments/{id}/edit.
9. WHEN the Author edits and saves a moment, THE Moment_Detail SHALL reflect the updated content within 60 seconds.
10. THE CMS SHALL allow the Author to delete a moment; THE CMS SHALL require the Author to confirm the deletion before proceeding.
11. WHEN the Author deletes a moment, THE Moment_List SHALL no longer display the deleted moment within 60 seconds; THE Storage SHALL delete all associated photos from S3 and remove all associated records from the database.
12. THE CMS SHALL be accessible only to the Author via the existing JWT authentication mechanism.

---

### Requirement 6: Infrastructure and Performance

**User Story:** As the Author, I want the Emi's Big Moments section to use the same infrastructure as the rest of the website, so that I do not need to manage additional services.

#### Acceptance Criteria

1. THE Website SHALL serve the Emi's Big Moments section over HTTPS at emisofia.com/moments.
2. THE Website SHALL serve moment photos via AWS CloudFront (CDN) for fast delivery.
3. THE Storage SHALL use AWS S3 to persist moment photos durably, with no data loss under normal operating conditions.
4. THE Storage SHALL use the existing SQLite database to persist moment metadata (title, date, description, status, photo records).
5. WHEN a visitor loads the Moment_List page, THE Website SHALL return the fully rendered HTML within 3 seconds on a connection with at least 5 Mbps bandwidth.
6. WHEN a visitor loads the Moment_Detail page, THE Website SHALL return the fully rendered HTML within 3 seconds on a connection with at least 5 Mbps bandwidth.
7. THE Emi's Big Moments backend endpoints SHALL be part of the existing FastAPI application, requiring no additional server processes.
8. THE Emi's Big Moments frontend pages SHALL be part of the existing Next.js application, requiring no additional build configurations.
