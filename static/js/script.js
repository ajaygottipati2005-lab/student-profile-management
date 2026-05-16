// Function to load sections based on selected branch
function loadSections(branchSelectId, sectionSelectId) {
    const branchSelect = document.getElementById(branchSelectId);
    const sectionSelect = document.getElementById(sectionSelectId);

    if (!branchSelect || !sectionSelect) return;

    branchSelect.addEventListener('change', function() {
        const branch = this.value;
        const sectionSelect = document.getElementById(sectionSelectId);

        // Clear current options
        sectionSelect.innerHTML = '<option value="">Select Section</option>';

        if (branch) {
            // Fetch sections for the selected branch
            fetch(`/section_options?branch=${encodeURIComponent(branch)}`)
                .then(response => response.json())
                .then(sections => {
                    sections.forEach(section => {
                        const option = document.createElement('option');
                        option.value = section;
                        option.textContent = section;
                        sectionSelect.appendChild(option);
                    });
                })
                .catch(error => {
                    console.error('Error loading sections:', error);
                });
        }
    });
}

// Function to load subjects based on year, semester, and branch
function loadSubjects(yearSelectId, semesterSelectId, branchSelectId, subjectSelectId) {
    const yearSelect = document.getElementById(yearSelectId);
    const semesterSelect = document.getElementById(semesterSelectId);
    const branchSelect = document.getElementById(branchSelectId);
    const subjectSelect = document.getElementById(subjectSelectId);

    if (!yearSelect || !semesterSelect || !branchSelect || !subjectSelect) return;

    function updateSubjects() {
        const year = yearSelect.value;
        const semester = semesterSelect.value;
        const branch = branchSelect.value;

        // Clear current options
        subjectSelect.innerHTML = '<option value="">Select Subject</option>';

        if (year && semester && branch) {
            // Fetch subjects for the selected criteria
            fetch(`/subject_options?year=${year}&semester=${semester}&branch=${encodeURIComponent(branch)}`)
                .then(response => response.json())
                .then(subjects => {
                    subjects.forEach(subject => {
                        const option = document.createElement('option');
                        option.value = subject;
                        option.textContent = subject;
                        subjectSelect.appendChild(option);
                    });
                })
                .catch(error => {
                    console.error('Error loading subjects:', error);
                });
        }
    }

    yearSelect.addEventListener('change', updateSubjects);
    semesterSelect.addEventListener('change', updateSubjects);
    branchSelect.addEventListener('change', updateSubjects);
}

// Initialize dynamic loading for staff attendance page
document.addEventListener('DOMContentLoaded', function() {
    // For staff attendance page
    loadSections('branch-select', 'section-select');
    loadSubjects('year-select', 'semester-select', 'branch-select', 'subject-select');

    // For analyze attendance page
    loadSections('branch', 'section');
    loadSubjects('year', 'semester', 'branch', 'subject-select'); // If there's a subject select on analyze page
});