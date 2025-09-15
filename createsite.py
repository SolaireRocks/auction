import json
import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv

# --- CORRECTED HTML TEMPLATE ---
# This version uses a safe data island and robust JavaScript to prevent parsing issues.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Auction Item Analysis</title>
    <style>
        :root {
            --bg-color: #1a1a1a; --table-bg-color: #2c2c2c; --header-bg-color: #3a3a3a;
            --header-hover-bg-color: #4a4a4a; --row-even-bg-color: #333333; --row-odd-bg-color: #2c2c2c;
            --border-color: #444444; --text-color: #e0e0e0; --link-color: #4a90e2;
            --link-hover-color: #81b5f5; --sort-indicator-color: #81b5f5;
        }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: var(--bg-color); color: var(--text-color); margin: 0; padding: 2rem; line-height: 1.6; }
        h1 { text-align: center; color: #ffffff; font-weight: 300; margin-bottom: 2rem; }
        .table-container { max-width: 1200px; margin: auto; overflow-x: auto; border-radius: 8px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3); }
        table { width: 100%; border-collapse: collapse; background-color: var(--table-bg-color); border-spacing: 0; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid var(--border-color); }
        thead th { background-color: var(--header-bg-color); color: #ffffff; font-weight: 600; position: sticky; top: 0; z-index: 10; }
        thead th[data-column] { cursor: pointer; transition: background-color 0.2s ease-in-out; user-select: none; }
        thead th[data-column]:hover { background-color: var(--header-hover-bg-color); }
        tbody tr:nth-child(even) { background-color: var(--row-even-bg-color); }
        tbody tr:nth-child(odd) { background-color: var(--row-odd-bg-color); }
        tbody tr:hover { background-color: var(--header-hover-bg-color); }
        td { font-size: 0.95em; }
        td:nth-child(3) { font-family: 'Courier New', Courier, monospace; text-align: right; white-space: nowrap; }
        td:nth-child(4) { text-align: center; }
        a { color: var(--link-color); text-decoration: none; transition: color 0.2s ease-in-out; }
        a:hover { color: var(--link-hover-color); text-decoration: underline; }
        .sort-indicator { color: var(--sort-indicator-color); font-size: 0.8em; margin-left: 8px; display: inline-block; width: 10px; }
    </style>
</head>
<body>
    <h1>Auction Item Analysis</h1>
    <div class="table-container"><table><thead><tr><th data-column="name">Item Name <span class="sort-indicator"></span></th><th data-column="category">Category <span class="sort-indicator"></span></th><th data-column="price">Market Value <span class="sort-indicator"></span></th><th>Google Search</th></tr></thead><tbody id="data-table-body"></tbody></table></div>
    
    <!-- JSON data is safely embedded here as plain text -->
    <script type="application/json" id="auctionData">
        __JSON_DATA_PLACEHOLDER__
    </script>

    <script>
        // Safely parse the JSON data from the data island
        const jsonData = JSON.parse(document.getElementById('auctionData').textContent);

        const tableBody = document.getElementById('data-table-body');
        const headers = document.querySelectorAll('thead th[data-column]');
        let currentSort = { column: 'price', isAscending: false };

        // This function now correctly extracts the item name regardless of the JSON structure.
        function getItemName(item) {
            if (typeof item.item_identification === 'object' && item.item_identification !== null) {
                return item.item_identification.item_name || 'N/A'; // Handle object structure
            }
            return item.item_identification; // Handle string structure
        }

        function getCategory(itemName) {
            const name = itemName.toLowerCase();
            if (name.includes('furniture') || name.includes('highboy') || name.includes('table') || name.includes('nightstand') || name.includes('desk') || name.includes('cabinet') || name.includes('curio') || name.includes('sewing') || name.includes('dresser')) return 'Furniture';
            if (name.includes('painting') || name.includes('print') || name.includes('art') || name.includes('escher') || name.includes('audubon')) return 'Art/Prints';
            if (name.includes('dinnerware') || name.includes('china') || name.includes('porcelain') || name.includes('franciscan') || name.includes('belleek') || name.includes('lladro') || name.includes('goebel') || name.includes('hummel')) return 'Pottery/China';
            if (name.includes('mirror') || name.includes('sconce') || name.includes('lamp') || name.includes('lantern')) return 'Decor/Lighting';
            if (name.includes('glassware') || name.includes('crystal') || name.includes('decanter') || name.includes('lenox')) return 'Glassware';
            if (name.includes('blower') || name.includes('lawnmower') || name.includes('edger') || name.includes('vac') || name.includes('tool')) return 'Tools/Equipment';
            if (name.includes('nerf') || name.includes('train') || name.includes('toy')) return 'Toys/Games';
            if (name.includes('cards')) return 'Collectibles';
            return 'Miscellaneous';
        }
        
        function populateTable() {
            tableBody.innerHTML = '';
            jsonData.forEach(item => {
                const row = document.createElement('tr');
                const itemName = getItemName(item);
                
                const nameCell = document.createElement('td');
                const nameLink = document.createElement('a');
                nameLink.href = item.original_listing.url;
                nameLink.textContent = itemName;
                nameLink.target = "_blank";
                nameCell.appendChild(nameLink);
                
                const categoryCell = document.createElement('td');
                categoryCell.textContent = getCategory(itemName);

                const priceCell = document.createElement('td');
                priceCell.textContent = (item.estimated_market_value || 0).toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 });

                const linkCell = document.createElement('td');
                const searchLink = document.createElement('a');
                searchLink.href = `https://www.google.com/search?q=${encodeURIComponent(itemName)}`;
                searchLink.textContent = 'Search';
                searchLink.target = "_blank";
                linkCell.appendChild(searchLink);

                row.appendChild(nameCell);
                row.appendChild(categoryCell);
                row.appendChild(priceCell);
                row.appendChild(linkCell);

                tableBody.appendChild(row);
            });
        }
        
        function sortData(column) {
            const isNumeric = column === 'price';
            if (currentSort.column === column) {
                currentSort.isAscending = !currentSort.isAscending;
            } else {
                currentSort.column = column;
                currentSort.isAscending = !isNumeric; 
            }
            jsonData.sort((a, b) => {
                let valA, valB;
                if (isNumeric) {
                    valA = a.estimated_market_value || 0;
                    valB = b.estimated_market_value || 0;
                } else {
                    const nameA = getItemName(a);
                    const nameB = getItemName(b);
                    if (column === 'name') {
                        valA = nameA.toLowerCase();
                        valB = nameB.toLowerCase();
                    } else if (column === 'category') {
                        valA = getCategory(nameA);
                        valB = getCategory(nameB);
                    }
                }
                let comparison = 0;
                if (valA > valB) { comparison = 1; } else if (valA < valB) { comparison = -1; }
                return currentSort.isAscending ? comparison : comparison * -1;
            });
            updateSortIndicators();
            populateTable();
        }
        
        function updateSortIndicators() {
            headers.forEach(header => {
                const indicator = header.querySelector('.sort-indicator');
                if (header.dataset.column === currentSort.column) {
                    indicator.textContent = currentSort.isAscending ? ' ▲' : ' ▼';
                } else {
                    indicator.textContent = '';
                }
            });
        }
        
        headers.forEach(header => {
            header.addEventListener('click', () => { sortData(header.dataset.column); });
        });
        
        sortData('price');
    </script>
</body>
</html>
"""

def update_index_html(new_report_filename):
    """Adds a link to the new report at the top of index.html."""
    print(f"\n--- Updating index.html ---")
    index_path = "index.html"
    placeholder = "<!-- REPORT_LINKS_PLACEHOLDER -->"
    
    try:
        base_name = os.path.splitext(new_report_filename)[0]
        parts = base_name.split('_')
        site_name = "Transitional Design" if parts[0].startswith('trans') else "Great Finds"
        date_str = parts[-1]
        link_text = f"{site_name} Report - {date_str}"
    except IndexError:
        link_text = new_report_filename

    new_link_html = f'            <li><a href="{new_report_filename}">{link_text}</a></li>'

    try:
        with open(index_path, 'r+', encoding='utf-8') as f:
            content = f.read()
            if new_link_html not in content:
                f.seek(0)
                f.write(content.replace(placeholder, f"{placeholder}\n{new_link_html}"))
                print(f"Successfully added link for '{new_report_filename}' to index.html.")
            else:
                print("Link for this report already exists in index.html.")
        return True
    except FileNotFoundError:
        print(f"Error: index.html not found. Please ensure the base index.html file exists in this directory.")
        return False
    except Exception as e:
        print(f"An error occurred while updating index.html: {e}")
        return False

def commit_and_push_to_github(filenames_to_add, commit_message):
    """Adds, commits, and pushes specified files to GitHub."""
    print("\n--- Pushing updates to GitHub ---")
    try:
        subprocess.run(["git", "add"] + filenames_to_add, check=True, capture_output=True)
        commit_result = subprocess.run(["git", "commit", "-m", commit_message], check=True, capture_output=True, text=True)
        if "nothing to commit" in commit_result.stdout or "no changes added to commit" in commit_result.stdout:
            print("No new changes to commit. GitHub is already up to date.")
            return True
        subprocess.run(["git", "push"], check=True, capture_output=True)
        
        load_dotenv()
        username = os.getenv("GITHUB_USERNAME")
        repo_name = os.getenv("GITHUB_REPO_NAME")
        if username and repo_name:
            print(f"\nSuccess! View your updated archive at: https://{username}.github.io/{repo_name}/")
        else:
            print("\nSuccess! Push to GitHub complete.")
        return True

    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        # Check if the error output is available
        error_output = e.stderr if hasattr(e, 'stderr') and e.stderr else str(e)
        print(f"An error occurred during a Git operation: {error_output}")
        print("Please check your Git configuration, authentication, and repository status.")
        return False

def generate_html_from_template(json_filename):
    """Main function to create a report, update the index, and push to GitHub."""
    print(f"\n--- Processing '{json_filename}' ---")
    try:
        with open(json_filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Use json.dumps with indentation for readability in the HTML source
        json_data_string = json.dumps(data, indent=4)

        final_html_content = HTML_TEMPLATE.replace("__JSON_DATA_PLACEHOLDER__", json_data_string)
        
        base_name = os.path.splitext(json_filename)[0]
        date_str = datetime.now().strftime('%Y-%m-%d')
        # Ensure the filename is consistent with how update_index_html parses it
        prefix = "trans" if "trans" in base_name.lower() else "greatfinds"
        html_filename = f"{prefix}_Report_{date_str}.html"

        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(final_html_content)
        
        print(f"Successfully created report: '{html_filename}'")
        
        if update_index_html(html_filename):
            files_to_commit = [html_filename, "index.html"]
            commit_msg = f"Add report: {html_filename}"
            commit_and_push_to_github(files_to_commit, commit_msg)
            
    except FileNotFoundError:
        print(f"Error: The file '{json_filename}' was not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def main():
    """Prompts user and starts the process."""
    while True:
        json_filename_input = input("Please enter the name of the sorted JSON file to process: ")
        if os.path.exists(json_filename_input):
            generate_html_from_template(json_filename_input)
            break
        else:
            print(f"File '{json_filename_input}' not found. Please try again.")

if __name__ == "__main__":
    main()