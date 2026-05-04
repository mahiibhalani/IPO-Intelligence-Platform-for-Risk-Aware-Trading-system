# Agile Documentation Report

## 5. Agile Documentation

### 5.1 Agile Project Charter

#### Project Name
IPO Intelligence Platform for Risk-Aware Trading System

#### Project Vision
Build a user-friendly, intelligent web platform that empowers Indian investors and traders to analyze IPO opportunities with confidence. The system will combine data collection, financial analysis, sentiment analysis, and machine learning to generate risk-aware BUY/AVOID recommendations for IPOs.

#### Mission Statement
Deliver a reliable decision-support system that helps users identify promising IPOs, understand risk, and manage watchlists and applied IPOs—from initial research through listing performance.

#### Goals and Objectives
- Provide accurate IPO analysis based on fundamentals, market conditions, sentiment, and machine learning.
- Enable secure user registration, personalized watchlists, and portfolio management.
- Present data through clear visual dashboards and interactive IPO reports.
- Support investor decisions with risk scoring and rationale statements.
- Maintain high quality through rigorous testing and clean code standards.

#### Key Stakeholders
- Project Sponsor: Academic supervisor or development team lead
- Product Owner: Project author / business analyst
- Development Team: Frontend, backend, data science, and QA contributors
- End Users: Retail investors, active traders, financial analysts
- System Administrator: Deployment and maintenance support

#### Scope
**In scope**
- User authentication and profile management
- IPO data collection and storage
- Fundamental, sentiment, and market analysis modules
- ML-based IPO recommendation engine
- Interactive dashboard and IPO detail pages
- Watchlist and portfolio tracking
- Reporting and export capabilities

**Out of scope**
- Direct trade execution
- Full live stock-market trading platform
- Mobile native application
- Exchange-level connectivity such as direct NSE/BSE trading APIs

#### Critical Success Factors
- Timely delivery of core functionality for IPO analysis and recommendations
- Quality of recommendations backed by explainable analysis
- Usable interface with effective visualization and minimal friction
- Reliable authentication and data persistence
- Well-documented code and reproducible test results

#### Constraints
- Limited development time due to academic deadlines
- Use of available open-source tools and libraries
- Dependence on data accessibility and format consistency
- Deployment on a single server or local environment

#### Assumptions
- IPO data sources are accessible and contain sufficient content for analysis
- Users are familiar with basic investing terminology
- The backend can support moderate concurrency for demo use
- Project will run on Python 3.9+ and modern browser versions

### 5.2 Agile Roadmap / Schedule

#### High-Level Roadmap
- **Week 1**: Requirement gathering, architecture design, environment setup
- **Week 2**: Backend development and database modeling
- **Week 3**: Data collection, analysis modules, and ML pipeline
- **Week 4**: Frontend dashboard, IPO detail pages, watchlist features
- **Week 5**: Integration, testing, bug fixing, and documentation
- **Week 6**: Final polishing, deployment preparation, presentation materials

#### Milestones
- **M1: Project Initiation**
  - Kickoff meeting
  - Requirement definition and charter approval
  - Project board and backlog created
- **M2: Data & Backend Core**
  - Database models complete
  - IPO collection and fundamental analysis ready
- **M3: Intelligence Engine**
  - Sentiment analysis module complete
  - ML prediction engine trained and validated
- **M4: UI and Reporting**
  - Dashboard and IPO details pages implemented
  - Watchlist and portfolio screens functional
- **M5: Quality and Delivery**
  - Test plan executed
  - User acceptance checklist completed
  - Documentation and final report ready

#### Key Dates
- Start Date: May 1, 2026
- End Date: June 15, 2026
- Review Checkpoints: May 7, May 14, May 21, May 28, June 5, June 12

#### Release Schedule
- **Release 1.0 (MVP)**: Early June — core IPO analytics and recommendation flow
- **Release 1.1**: Mid June — UI improvements, watchlist, and portfolio enhancements
- **Release 1.2**: Final deliverable — documentation, deployment guide, and testing summary

### 5.3 Agile Project Plan

#### Sprint Structure
- **Sprint Duration**: 1 week each
- **Total Sprints**: 6
- **Sprint Planning**: Prioritize backlog items and define sprint goals
- **Daily Standup**: Brief progress updates and impediment tracking
- **Sprint Review**: Demonstrate completed work
- **Sprint Retrospective**: Identify process improvements

#### Sprint Breakdown

**Sprint 1: Foundation**
- Define backlog and user stories
- Setup repository, environment, and tools
- Configure Flask backend and SQLite database
- Create basic user authentication
- Create initial project documentation

**Sprint 2: Data and Analysis Core**
- Develop IPO data collector component
- Implement IPO data models
- Build fundamental analysis module
- Create data ingestion pipeline
- Add initial database seed data

**Sprint 3: Intelligence Modules**
- Implement sentiment analyzer
- Build market analysis component
- Develop ML predictor and training pipeline
- Integrate analysis results into backend
- Validate model predictions on sample IPOs

**Sprint 4: Frontend Dashboard**
- Implement dashboard layout and navigation
- Build IPO list and IPO detail views
- Add visualization charts (Plotly, graphs, tables)
- Connect frontend with backend APIs
- Implement watchlist and portfolio pages

**Sprint 5: Integration and Quality**
- Complete end-to-end integration
- Add alerting and notification placeholders
- Develop unit and integration tests
- Fix defects and performance issues
- Review code quality and documentation

**Sprint 6: Final Delivery**
- Run final test plan and acceptance checks
- Polish UI, copy, and content
- Produce final presentation and report
- Prepare deployment and setup notes
- Conduct final retrospective and archive backlog

#### Roles and Responsibilities
- **Product Owner**: Defines and prioritizes requirements, provides feedback
- **Scrum Master**: Facilitates team process, removes blockers
- **Developer(s)**: Build backend, frontend, and analytics modules
- **QA/Test Engineer**: Creates and runs test cases, verifies features
- **Documentation Lead**: Writes reports, diagrams, and user guidance

### 5.4 Agile User Story (Minimum 3 Tasks)

#### User Story 1: IPO Research and Recommendation
- **Title**: As an investor, I want to view IPO analysis so that I can decide whether to apply.
- **Acceptance Criteria**:
  1. The user can see a list of upcoming IPOs.
  2. The user can click an IPO and view detailed analysis.
  3. The platform shows a BUY / AVOID recommendation.
  4. The platform explains the key risk factors.
- **Tasks**:
  - Create IPO listing API endpoint
  - Build IPO details page with analysis summary
  - Implement decision engine to return recommendation
  - Add risk score and rationale text to the UI

#### User Story 2: Personal Watchlist Management
- **Title**: As a user, I want to save IPOs to a watchlist so that I can monitor them later.
- **Acceptance Criteria**:
  1. The user can mark any IPO as watched.
  2. The watchlist persists across sessions.
  3. The watchlist page displays current analysis status.
  4. The user can remove IPOs from the watchlist.
- **Tasks**:
  - Implement watchlist database model and API
  - Add watchlist action buttons to IPO cards
  - Build watchlist page/UI components
  - Create remove-watchlist functionality

#### User Story 3: Secure Access and Profile
- **Title**: As a registered user, I want to log in and view my profile so I can keep my data private.
- **Acceptance Criteria**:
  1. The user can register with email and password.
  2. The user can log in and access protected pages.
  3. The user can update profile details.
  4. The user can log out securely.
- **Tasks**:
  - Implement user registration and authentication flows
  - Add profile page with editable fields
  - Protect sensitive routes using login required
  - Create logout functionality and session management

#### User Story 4: Machine Learning Prediction
- **Title**: As an analyst, I want to see model predictions for IPO performance so I can compare data-driven insights.
- **Acceptance Criteria**:
  1. The platform returns a prediction score for each IPO.
  2. The prediction is stored with model version.
  3. The UI displays prediction confidence.
  4. The system uses trained model artifacts from the `models/saved` folder.
- **Tasks**:
  - Train ML models on IPO dataset
  - Save models as joblib artifacts
  - Create prediction endpoint using loaded model
  - Display prediction result in IPO detail view

### 5.5 Agile Release Plan

#### Release 1.0: MVP Demonstration
- **Scope**:
  - User login and registration
  - IPO data listing and details
  - Fundamental + sentiment analysis
  - Recommendation engine and risk summary
  - Watchlist support
- **Target Date**: Early June
- **Risk**: Incomplete model accuracy and data source stability

#### Release 1.1: Feature Expansion
- **Scope**:
  - Portfolio tracking
  - Improved visualization and search filters
  - Better user preferences and alert options
  - More robust analysis and model explainability
- **Target Date**: Mid June
- **Risk**: Additional integration effort and UI complexity

#### Release 1.2: Final Delivery
- **Scope**:
  - Final UI polish and bug fixes
  - Complete project documentation
  - Final testing and demo readiness
  - Deployment notes and setup instructions
- **Target Date**: June 15, 2026
- **Risk**: Time remaining for final checks and report preparation

### 5.6 Agile Sprint Backlog

#### Sprint Backlog Example

| User Story | Task | Priority | Status | Owner |
|------------|------|----------|--------|-------|
| IPO Research | Build IPO listing API | High | In Progress | Backend |
| IPO Research | Add IPO detail page | High | To Do | Frontend |
| Watchlist | Implement watchlist model | Medium | To Do | Backend |
| Watchlist | Build watchlist UI | Medium | To Do | Frontend |
| Auth | Add registration | High | Done | Backend |
| Auth | Protect routes | High | In Progress | Backend |
| ML Prediction | Train model | High | Done | Data Science |
| ML Prediction | Add prediction display | Medium | To Do | Frontend |
| Testing | Create unit tests | High | In Progress | QA |
| Documentation | Write Agile report | Medium | In Progress | Documentation Lead |

#### Typical Sprint Backlog Activities
- Sprint planning and backlog refinement
- Design API contracts and UI wireframes
- Implement feature tasks and complete acceptance criteria
- Test code and fix defects
- Document progress and demonstrate features
- Retrospect on process improvement

### 5.7 Agile Test Plan

#### Test Plan Overview
The test plan for the IPO Intelligence Platform covers unit tests, integration tests, and acceptance tests. It ensures that the application is reliable, secure, and meets user requirements.

#### Test Objectives
- Validate core functionality for IPO analysis and user workflow
- Ensure API endpoints return correct data and status codes
- Confirm machine learning predictions are computed and displayed correctly
- Verify user authentication and session protection
- Test UI navigation and data presentation
- Detect and fix regressions before final delivery

#### Test Types

**Unit Tests**
- Verify functions such as data validation, score calculation, and model loading
- Test database model methods and serialization
- Confirm route helpers and utility classes behave correctly

**Integration Tests**
- Test end-to-end backend API flows
- Validate frontend and backend communication for core pages
- Ensure analysis modules combine outputs correctly in the decision engine

**Acceptance Tests**
- Confirm registered user can log in and view dashboard
- Verify IPO list loads and IPO detail page shows recommendation
- Test watchlist addition and removal behavior
- Validate model prediction is visible on the IPO report page

#### Key Test Cases
1. **User registration and login**
   - Register a user with valid credentials
   - Attempt registration with duplicate email
   - Log in with valid credentials
   - Reject login with invalid password
2. **IPO listing and filtering**
   - Load IPO list successfully
   - Search IPO by company name and sector
   - Filter IPOs by status and recommendation
3. **Analysis results**
   - Retrieve IPO analysis data for a selected IPO
   - Confirm the recommendation field exists and is one of BUY/HOLD/AVOID
   - Validate risk level assignment and confidence score range
4. **Watchlist behavior**
   - Add IPO to watchlist
   - Ensure watchlist item persists after refresh
   - Remove IPO from watchlist
5. **ML prediction module**
   - Load the saved model artifact successfully
   - Predict an IPO score from sample input
   - Verify the UI displays the prediction value
6. **Security and authorization**
   - Protected route cannot be accessed without login
   - User logout clears session
   - Password storage uses hash rather than plaintext

#### Test Environments
- Local development environment with SQLite database
- Browser compatibility: Chrome, Firefox, Edge
- Python 3.9+ with required dependencies installed
- Frontend served through Vite development server or production build

#### Tools and Frameworks
- Backend: `pytest`, `unittest`, `Flask-Testing`
- ML module: `scikit-learn`, `joblib`
- Frontend: `Jest`, `React Testing Library`
- Static analysis: `flake8`, `mypy` (optional)

#### Test Reporting
- Track executed test cases and pass/fail status
- Identify defects, assign severity, and document resolution
- Summarize coverage for unit and integration tests
- Record test results in project report and final presentation

### 5.8 Earned-value and Burn Charts

#### Earned Value Management (EVM)
Earned value tracking helps measure project progress against planned work. For this project, the core metrics are:
- **Planned Value (PV)**: Estimated work value for completed schedule items
- **Earned Value (EV)**: Actual work value completed
- **Actual Cost (AC)**: Time spent or effort used to complete tasks

Example calculations for a 6-week project:
- Total planned points = 100 story points
- Week 1 PV = 15, Week 2 PV = 30, Week 3 PV = 50, Week 4 PV = 70, Week 5 PV = 85, Week 6 PV = 100
- If Week 3 completed 45 points, EV=45
- If actual effort is 50 hours for Week 3, AC=50

Key metrics:
- **Schedule Variance (SV)** = EV - PV
- **Cost Variance (CV)** = EV - AC
- **Schedule Performance Index (SPI)** = EV / PV
- **Cost Performance Index (CPI)** = EV / AC

#### Burn Down Chart
A burn down chart records remaining work over time for a sprint or project. Use weekly checkpoints to visualize progress.

Example data points:
- Sprint 1 start: 100 points remaining
- Sprint 1 end: 80 points remaining
- Sprint 2 end: 65 points remaining
- Sprint 3 end: 48 points remaining
- Sprint 4 end: 28 points remaining
- Sprint 5 end: 12 points remaining
- Sprint 6 end: 0 points remaining

The burn down chart shows a steady decline in remaining work as tasks are completed. If the line flattens, the team should investigate impediments.

#### Burn Up Chart
A burn up chart tracks work completed against total scope.
- Plot total scope line at 100 points
- Plot completed work line rising from 0 to 100
- Visualize scope changes if new features are added

#### Practical Example for This Project
- **Week 1**: 12 points completed out of 15 → EV = 12, PV = 15, SV = -3
- **Week 2**: 18 points completed out of 15 → EV = 30, PV = 30, SV = 0
- **Week 3**: 17 points completed out of 20 → EV = 47, PV = 50, SV = -3
- **Week 4**: 20 points completed out of 20 → EV = 67, PV = 70, SV = -3
- **Week 5**: 18 points completed out of 15 → EV = 85, PV = 85, SV = 0
- **Week 6**: 15 points completed out of 15 → EV = 100, PV = 100, SV = 0

#### Reporting and Review
- Update the burn chart weekly after sprint review
- Use earned value to assess whether the team is ahead or behind schedule
- Adjust scope or effort if schedule variance remains negative
- Document outcomes in sprint retrospectives

---

## Summary
This Agile documentation report provides a detailed project charter, roadmap, plan, user stories, release plan, sprint backlog, test plan, and earned-value/burn chart guidance tailored to the IPO Intelligence Platform. It is designed to support your final project documentation and implementation phases.
