$(document).ready(function() {
    console.log("Global script loaded.");

    // Example: Add active class to navbar link based on current page
    // (This is handled better in the base.html using Jinja's request.endpoint)

    // Example: Initialize tooltips if you use them
    // $('[data-toggle="tooltip"]').tooltip();

    // --- Search Form Handling ---
    // The base template now uses a standard GET form submission
    // for search, redirecting to e.g., /list_devices?q=searchTerm.
    // No specific JS is needed here for that simple redirection behavior.
    // If you wanted AJAX search results *on the same page*,
    // you would add that logic here, preventing default form submission
    // and updating a results container.

    /*
    // Example of how AJAX search *could* be implemented (if desired):
    $('#searchForm').on('submit', function(event) {
        event.preventDefault(); // Stop the default form submission
        var searchTerm = $('#searchInput').val();
        if (searchTerm.length < 2) {
            // Optional: Add feedback if search term is too short
            return;
        }

        // Show some loading indicator
        // $('#searchResultsContainer').html('<p>Loading...</p>');

        $.ajax({
            url: '/your_ajax_search_endpoint', // Endpoint that returns JSON results
            type: 'GET', // or 'POST'
            data: { q: searchTerm },
            success: function(response) {
                // Hide loading indicator
                // Render the results in '#searchResultsContainer'
                // e.g., $('#searchResultsContainer').html(response.html_results);
                 console.log("Search successful:", response);
                 alert("AJAX Search not fully implemented yet. Check console.");
            },
            error: function(xhr, status, error) {
                // Hide loading indicator
                // Show error message
                console.error("Search failed:", error);
                 //$('#searchResultsContainer').html('<p>Error loading results.</p>');
                 alert("Search failed. Please try again later.");
            }
        });
    });
    */

});