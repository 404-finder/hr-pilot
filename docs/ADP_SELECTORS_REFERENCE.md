# ADP Selectors Reference

## Document Information
- **Date Collected:** February 11, 2026
- **ADP System:** Workforce Now (WFN)
- **Workflow:** New Hire Creation + Registration Code Delivery
- **Browser Used:** Chrome/Chromium (for Playwright automation)

---

## Table of Contents
1. [Login Flow](#login-flow)
2. [Navigation to New Hire Form](#navigation-to-new-hire-form)
3. [Personal Information Section](#personal-information-section)
4. [Ask the New Hire Modal](#ask-the-new-hire-modal)
5. [Employment Section](#employment-section)
6. [Payroll Section](#payroll-section)
7. [Tax Section](#tax-section)
8. [Direct Deposit Section](#direct-deposit-section-optional)
9. [Save and Exit](#save-and-exit)
10. [Registration Code Delivery](#registration-code-delivery)

---

## Login Flow

### Login Page URL
```
https://online.adp.com/signin/v1/?APPID=WFNPortal&productId=80e309c3-7085-bae1-e053-3505430b5495&returnURL=https://workforcenow.adp.com/&callingAppId=WFN
```

### Selectors

| Element | Selector | Value/Notes |
|---------|----------|-------------|
| Username Input | `input[autocomplete="username"]` | - |
| Next Button | `#verifUseridBtn` | Click after entering username |
| Password Input | `input[autocomplete="current-password"]` | Appears after clicking Next |
| Sign In Button | `#signBtn` | Final login button |

### Flow
1. Navigate to login URL
2. Fill username → Click Next
3. Fill password → Click Sign In
4. Wait for redirect to WFN dashboard

---

## Navigation to New Hire Form

### Post-Login Navigation Path
Dashboard → Process → Hire/Rehire → Go to Hire → HR PR New Hires

### Selectors

| Element | Selector | Value/Notes |
|---------|----------|-------------|
| Process Menu Button | `button:has-text("Process")` | Top navigation menu |
| Hire/Rehire Link | `a[href="#/Process/ProcessTabHRCategoryHireRehire"]` | From Process dropdown |
| Go to Hire Button | `#navigateToNewHireViewId` | - |
| HR PR New Hires Card | `sdf-box:has-text("HR PR New Hires")` | Click entire card/tile |

### Flow
1. Click "Process" button
2. Click "Hire/Rehire" link
3. Click "Go to Hire" button
4. Click "HR PR New Hires" card

---

## Personal Information Section

### Form Fields

| Field | Selector | Value/Format | Required |
|-------|----------|--------------|----------|
| First Name | `#Name\.first` or `input[name="firstName"]` | Text | Yes |
| Last Name | `#Name\.last` or `input[name="lastName"]` | Text | Yes |
| Phone Number | `#rec_textbox_mobile` or `input[data-testid="phone-input"]` | Phone format | Yes |
| Use for Notification Checkbox | `input[name="useFrNotifyOnChangeId"]` | Always check this | Yes |
| Personal Email | `#homeEmail` or `input[name="homeEmail"]` | Email format | Yes |
| Hire Date | `#HireDate` or `input[name="hireDate"]` | mm/dd/yyyy | Yes |
| Reason for Hire | `#ReasonForHire` | "NEW - New Position" (typical) | Yes |
| Company Code | `#CompanyCode` | "ZKT LC Texas LLC" (typical) | Yes |
| Tax ID Type | `#TaxIdComponent_taxidtype` | "United States Social Security Number (SSN)" (always) | Yes |
| **Associate ID** | `#AssociateID` or `input[name="assocId"]` | **CAPTURE THIS VALUE** for later use | Auto-generated |

### Important Notes
- **Associate ID** is auto-generated and displayed on this form
- **MUST capture Associate ID** to use later for registration code delivery
- SSN, DOB, and Address fields are delegated to the new hire via "Ask the New Hire" flow

---

## Ask the New Hire Modal

### Opening the Modal

| Element | Selector | Notes |
|---------|----------|-------|
| Ask the New Hire Button | `#ENHAskNewhire` | Opens overlay modal |

### Modal Fields and Sub-Flows

#### 1. Assign Onboarding Experience

| Element | Selector | Value/Notes |
|---------|----------|-------------|
| Assign Onboarding Button | `#assignedTemplateName_Id` | Pencil icon button |
| Onboarding Experience Dropdown | `#onboardingTemplateId` | Opens in sub-modal |
| Select Experience | - | "Texas Experience LC Texas" (always) |
| Assign Button | `#ENHAssignOBExp` | Confirms selection |
| Back Button | `#back-button-with-label` | Closes sub-modal |

**Sub-flow:**
1. Click `#assignedTemplateName_Id`
2. Select "Texas Experience LC Texas" from `#onboardingTemplateId`
3. Click `#ENHAssignOBExp` (Assign)
4. Click `#back-button-with-label` (Back)

#### 2. Worked In State

| Element | Selector | Value |
|---------|----------|-------|
| Worked In State Dropdown | `#workedInState` | "TX - Texas" (always) |

#### 3. Reports To (Manager Assignment)

| Element | Selector | Value/Notes |
|---------|----------|-------------|
| Reports To Button | `#openReportsToCustomSlider_Id` | Opens manager search modal |
| Manager Name Search | `#onReportsToSearch` | Enter manager name |
| Search Button | `#reportsToSearch_Id` | Execute search |
| Manager Radio Button | `sdf-radio-button[aria-checked="true"]` | Select manager from results |
| Save Button | `#populateReportToValue_Id` | Confirm manager selection |

**Sub-flow:**
1. Click `#openReportsToCustomSlider_Id`
2. Enter manager name in `#onReportsToSearch`
3. Click `#reportsToSearch_Id`
4. Click radio button next to desired manager
5. Click `#populateReportToValue_Id` (Save)

#### 4. E-Verify Work Location

| Element | Selector | Value/Notes |
|---------|----------|-------------|
| E-Verify Location Dropdown | `#eVerifyLocationSelectBox` | Select store location (varies) |

#### 5. Save Modal

| Element | Selector | Notes |
|---------|----------|-------|
| Save Button | `#ENHInitiatePrehire` | Closes "Ask the New Hire" modal |

### Complete Modal Flow
1. Click "Ask the New Hire" button
2. Assign onboarding experience (sub-flow)
3. Select "TX - Texas" from Worked In State
4. Assign manager via Reports To (sub-flow)
5. Select store location from E-Verify Work Location
6. Click Save to close modal

---

## Proceeding to Next Section

### After Personal Section

| Element | Selector | Notes |
|---------|----------|-------|
| Next Button | `#OE_Next_Prim_btn_Id` | Proceed to Employment section |
| Validation Popup - Go to Next | `sdf-button[aria-label="Go to Next Section"]` | Click if validation popup appears |

**Note:** A validation popup will appear warning about missing fields (SSN, DOB, Address) - these are intentionally left blank for the new hire to complete. Click "Go to Next Section" to proceed.

---

## Employment Section

### Form Fields

| Field | Selector | Value/Format | Required |
|-------|----------|--------------|----------|
| Job Title | `#jobTitleList_Id_div` or `input[aria-label="Job Title"]` | "TEAMMEMB - TEAM MEMBER" (typical) | Yes |
| Worker Category | `#workersCategry_Id` or `input[aria-label="Worker Category"]` | "RPT - REGULAR PART TIME" (typical) | Yes |
| Benefits Eligibility Class | `#benEligClassList_Id` or `input[aria-label="Benefits Eligibility Class"]` | "BE - Benefit Eligible Team Members" (always) | Yes |
| Calculate Using Measurement Periods | `sdf-radio-button[value="C"]` | Radio button - select this option | Yes |
| Home Department | `#homeDep_Id` or `input[aria-label="Home Department"]` | Varies by location/role | Yes |

### Proceeding to Next Section

| Element | Selector | Notes |
|---------|----------|-------|
| Next Button | `button.vdl-button--primary:has-text("Next")` | Proceed to Payroll section |
| Validation Popup - Go to Next | `sdf-button[aria-label="Go to next section"]` | Click if validation popup appears |

---

## Payroll Section

### Form Fields

| Field | Selector | Value/Format | Required |
|-------|----------|--------------|----------|
| Compensation Type | `#regPayRate` (the dropdown) | "Hourly" (always) | Yes |
| Regular Pay Rate | `#SalaryPerPay` or `input[name="payName"]` | XX.XX (e.g., "15.50") | Yes |
| Pay Frequency | - | "Biweekly" (pre-set, no action needed) | Pre-set |

### Proceeding to Next Section

| Element | Selector | Notes |
|---------|----------|-------|
| Next Button | `button.vdl-button--primary:has-text("Next")` | Proceed to Tax section |

---

## Tax Section

### Form Fields

| Field | Selector | Value/Format | Required |
|-------|----------|--------------|----------|
| SUI/SDI Tax Code | `#suisdiTax` or `input[aria-label="SUI/SDI Tax Code"]` | "TX -53 -Texas" (only option) | Yes |

### Proceeding to Next Section

| Element | Selector | Notes |
|---------|----------|-------|
| Next Button | `#taxNext_Id` or `button[name="taxNext"]` | Proceed to Direct Deposit section |

---

## Direct Deposit Section (Optional)

**Note:** This entire section is optional and may be skipped if direct deposit info is not available.

### Form Fields

| Field | Selector | Value/Format | Required |
|-------|----------|--------------|----------|
| Deduction Code | `#deductionCodeId__0` | "CK1 - CHECKING - CK1" (typical) | If filling DD |
| Verify Account Toggle | `#bypassPrenoteToggleSwitch_0` or `input[name="bypassPrenote_0"]` | Set to OFF (unchecked) = "No" | If filling DD |
| Routing Number | `#transitABANumber_0` or `input[aria-label="Routing Number"]` | 9-digit routing number | If filling DD |
| Account Number | `#bankDepAccNumber_0` or `input[aria-label="Account Number"]` | Account number (max 17 chars) | If filling DD |

### Proceeding to Next Section

| Element | Selector | Notes |
|---------|----------|-------|
| Next Button | `button[name="ddNext"]` | Proceed to Emergency Contact section |

---

## Emergency Contact Section

**Note:** This section is skipped - emergency contact info will be filled by the new hire.

### Skipping the Section

| Element | Selector | Notes |
|---------|----------|-------|
| Next Button | `button.vdl-button--primary:has-text("Next")` | Skip to review/return to Personal section |

---

## Save and Exit

### Final Save

After completing the form loop (returns to Personal section after Emergency Contact):

| Element | Selector | Notes |
|---------|----------|-------|
| Save and Exit Button | `#ENHSaveAndExit` | Saves new hire and returns to "In-Progress Hires" page |

### Expected Outcome
- Redirected to "In-Progress Hires" tab on the Hire page
- New hire is saved but not yet activated (pending registration code)

---

## Registration Code Delivery

### Navigation to Security Management

**Starting Point:** In-Progress Hires page

| Element | Selector | Notes |
|---------|----------|-------|
| Setup Menu Button | `button:has-text("Setup")` | Top navigation menu |
| Security Management Link | `a[href="#/pracSetup/pracSecurityManagement"]` | From Setup dropdown |

**Flow:**
1. Click "Setup" button
2. Click "Security Management" link
3. Redirected to: `https://netsecure.adp.com/revadm/strong/theme.faces`

### Navigation to Personal Registration Codes

**Note:** This is a different ADP portal using Dojo framework.

| Element | Selector | Notes |
|---------|----------|-------|
| People Menu (hover) | `#People_navItem` or `span[id="People_navItem_label"]` | Hover to reveal dropdown |
| Personal Registration Codes Link | `#People_ttd_Access\&Security_PersonalRegistrationCodes` or `span[href="/revadm/strong/people/pic/picManagement.faces"]` | Click from People dropdown |

**Flow:**
1. Hover over "People" menu
2. Click "Personal Registration Codes" link

### Search for New Hire

**Recommendation:** Use Associate ID for unique identification.

| Field | Selector | Value/Notes |
|-------|----------|-------------|
| Last Name Search | `#userLastName` or `input[name="searchform:userLastName"]` | Optional |
| First Name Search | `#userFirstName` or `input[name="searchform:userFirstName"]` | Optional |
| **Associate ID Search (PREFERRED)** | `#empId` or `input[name="searchform:empId"]` | **Use the captured Associate ID** from Personal section |
| Search Button | `#formSaveButton` or `input[name="searchform:formSaveButton"]` | Execute search |

**Flow:**
1. Enter **Associate ID** in `#empId` (captured from earlier)
2. Click Search button `#formSaveButton`

### Select Employee and Send Code

| Element | Selector | Notes |
|---------|----------|-------|
| Employee Checkbox | `img[id="tableGrid.store.rows[0].cells[0]_widget"]` | First (and only) result when using Associate ID |
| Issue PRC Dropdown Arrow | `#picEmailActions_arrow` or `span[name="searchResultform:picEmailActions"]` | Click to open dropdown |
| Personal Email Address Option | `#picPersonalEmailMenuItem` or `tr[aria-label*="Personal Email Address"]` | **Always select this option** |
| Work Email Address Option | `#picWorkEmailMenuItem` | Alternative (not used) |
| View Codes on Screen Option | `#picWorkOnScreenMenuItem` | Alternative (not used) |
| Confirmation Popup - Yes | `#revit_form_Button_21` or `span[id="revit_form_Button_21_label"]:has-text("Yes")` | Confirm sending code |

**Flow:**
1. Click checkbox to select employee
2. Click "Issue Personal Registration Codes" dropdown arrow
3. Select "Personal Email Address"
4. Click "Yes" on confirmation popup

### Success Confirmation

**Expected Result:**
- Banner appears at top: "An email containing the personal registration code has been sent to user(s) with a valid and unique email address."
- Registration code email sent to new hire's personal email
- New hire can now complete their onboarding

---

## Complete New Hire Workflow Summary

### Part 1: Create New Hire (ADP WFN)

1. **Login**
   - Username → Next → Password → Sign In

2. **Navigate to Form**
   - Process → Hire/Rehire → Go to Hire → HR PR New Hires

3. **Personal Section**
   - Fill: First Name, Last Name, Phone, Email
   - Check "Use for Notification"
   - Fill: Hire Date, Reason for Hire, Company Code, Tax ID Type
   - **Capture Associate ID** (critical for later)
   - Click "Ask the New Hire" button:
     - Assign onboarding experience
     - Select worked in state
     - Assign manager
     - Select E-Verify location
     - Save modal

4. **Employment Section**
   - Job Title, Worker Category, Benefits Class
   - Measurement Periods radio button
   - Home Department

5. **Payroll Section**
   - Compensation Type: Hourly
   - Regular Pay Rate

6. **Tax Section**
   - SUI/SDI Tax Code: TX

7. **Direct Deposit (Optional)**
   - Can be skipped or filled with banking info

8. **Emergency Contact**
   - Skip (new hire will fill)

9. **Save and Exit**

### Part 2: Send Registration Code (Security Management)

1. **Navigate**
   - Setup → Security Management

2. **Access PRC Tool**
   - People → Personal Registration Codes

3. **Search & Send**
   - Search by Associate ID
   - Select employee checkbox
   - Issue PRC → Personal Email Address
   - Confirm Yes

4. **Verify Success**
   - Success banner appears
   - Email sent to new hire

---

## Important Notes

### Critical Data to Capture
- **Associate ID** from Personal section - needed for registration code delivery

### Validation Popups
- After Personal section: "Go to Next Section"
- After Employment section: "Go to next section"
- These appear because some fields are intentionally left blank for the new hire

### Framework Differences
- Main WFN uses modern web components (`sdf-button`, `vdl-textbox`)
- Security Management portal uses Dojo framework (`dijit`, `dijitButton`)
- Selectors reflect these differences

### React Select Dropdowns
Many dropdowns use React Select (`MDFSelectBox__input`):
- Click to open dropdown
- Type or select value
- May need to wait for dropdown options to load

### Always-the-Same Values
These values never change:
- Tax ID Type: "United States Social Security Number (SSN)"
- Worked In State: "TX - Texas"
- Benefits Eligibility Class: "BE - Benefit Eligible Team Members"
- Compensation Type: "Hourly"
- SUI/SDI Tax Code: "TX -53 -Texas"
- Registration Code delivery: Always "Personal Email Address"

### Usually-the-Same Values
These rarely change but could vary:
- Reason for Hire: "NEW - New Position"
- Company Code: "ZKT LC Texas LLC"
- Job Title: "TEAMMEMB - TEAM MEMBER"
- Worker Category: "RPT - REGULAR PART TIME"
- Onboarding Experience: "Texas Experience LC Texas"

### Always-Varies Values
These always depend on the specific hire:
- First Name, Last Name, Phone, Email
- Hire Date
- Pay Rate
- Manager (Reports To)
- E-Verify Work Location (store)
- Home Department
- Direct Deposit info (if provided)

---

## Troubleshooting

### Common Issues

1. **Selectors with special characters**
   - `#Name\.first` requires escaping the dot in CSS selectors
   - Playwright handles this: `page.locator("#Name\\.first")`

2. **Dynamic IDs**
   - Some elements have generated IDs (e.g., `revit_form_Button_21`)
   - May change between sessions - use aria-label or text content as backup

3. **Dropdown timing**
   - React Select dropdowns need time to load options
   - Use `wait_for_selector` before selecting

4. **Modal overlays**
   - Modals may block underlying elements
   - Wait for modal to appear before interacting
   - Ensure modal is closed before proceeding

5. **Table row indices**
   - `tableGrid.store.rows[0]` assumes first result
   - With Associate ID search, there's only one result
   - If using name search, may need to handle multiple results

---

## Update History

- **2026-02-11:** Initial documentation - Complete new hire + registration code workflow
