class MainAgent:
    
    def __init__(self, query):
        import google.generativeai as genai
        API_KEY = "AIzaSyDju66-JtD42JqKy6Af5jxJGNGU5kBdNlI"
        self.query = query
        genai.configure(api_key = API_KEY)
        self.model = genai.GenerativeModel("gemini-2.0-flash-exp")

    def generate(self):
        formatting_agent = FormattingAgent(model = self.model, query=self.query)
        formatted_query = formatting_agent.format()

        print(f"This is the formatted query : {formatted_query}")

        dataset_gen_agent = DatasetGenerationAgent(formatted_query=formatted_query, model=self.model)
        script = dataset_gen_agent.generate()

        print(f"Script : {script}")
        
        exec_agent = ScriptExecutionAgent(script)
        output = exec_agent.execute()
        viz_agent = VizAgent(model=self.model, dataset_path="generated_dataset.csv")
        viz_script = viz_agent.generate_viz_script()
        viz_exec = ScriptExecutionAgent(viz_script)
        viz_output = viz_exec.execute()


        return output, viz_output

class FormattingAgent:
  

    def __init__(self, model, query):
        self.model = model
        self.query = query

    def format(self):
        import json
        prompt = f"""
                You are a data specification agent tasked with transforming a user's dataset request into a clear, structured data generation plan for CSV output.

                Given the user's request, produce:

                1) **Dataset Name:** : Must be generated_dataset.csv
                2) **Number of Rows:** Infer or ask for the quantity of data (default to 1000 rows if unspecified).  
                3) **Columns Specification:** For each column, define:
                - Column Name
                - Data Type (e.g., string, integer, float, date, boolean)
                - Example Values or Format (e.g., names, emails, dates in YYYY-MM-DD, integers between 1-100)
                - Constraints (if any, e.g., unique, non-null, within a range)

                4) **Special Notes:** Any requirements like relationships between columns, data distributions, or privacy needs (e.g., anonymization, realistic values).

                ---
                5) The query you generate will go to a model which generates a script based off your query, so keep your query simplistic, and ensure that the final script always works.
                👉 User request:
                "{self.query}"

            

                """
        response = self.model.generate_content(prompt)
        text = response.text
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]

        return text
    

class DatasetGenerationAgent:
    def __init__(self, formatted_query, model):
        self.query = formatted_query
        self.model = model

    def generate(self):
        prompt = f"""
                You are an expert Python data engineer. Your task is to write a complete Python script using pandas and numpy to generate a synthetic dataset as per the specification provided.

                ✅ The script should:
                - Import all necessary libraries (e.g., pandas, numpy)
                - Generate realistic data respecting the column types, constraints, and relationships
                - Use randomization, but follow constraints (e.g., value ranges, unique values where required)
                - Handle any correlations or dependencies between columns as noted
                - Use significant coefficients for scalars to ensure significant correlations.
                - Save the dataset as a CSV file called generated_dataset.csv
                - Include no extra explanations, just the code

                ---

                👉 Dataset specification:
                {self.query}

                ---

                👉 Your output:
                A Python script (as plain code, no formatting tags or comments) that generates the dataset and writes it to a CSV.
                """
        response = self.model.generate_content(prompt)
        text = response.text
        if text.endswith("```"):
            text = text[:-3]
        
        if text.startswith("```"):
            text = text[3:]

        return text
        
class ScriptExecutionAgent:
    def __init__(self, script):
        
        self.script_text = script
        self.clean_script()


    def clean_script(self):
    
        lines = self.script_text.splitlines()
        cleaned_lines = []
        for line in lines:
            if line.strip().lower() == 'python':
                continue
            if line.strip().startswith('```'):
                continue
            cleaned_lines.append(line)
        self.script_text = "\n".join(cleaned_lines)

    def execute(self):
        import tempfile
        import subprocess
        import os

        with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as tmp_file:
            tmp_file.write(self.script_text.encode('utf-8'))
            script_path = tmp_file.name
        
        try:
            result = subprocess.run(
                ['python', script_path],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                return {
                    'status': 'success',
                    'stdout': result.stdout,
                    'script_path': script_path,
                    'message': 'Script executed successfully.'
                }
            
            else:
                return {
                    'status': 'error',
                    'stderr': result.stderr,
                    'stdout': result.stdout,
                    'script_path': script_path,
                    'message': 'Script executed with errors.'
                }
            
        except subprocess.TimeoutExpired:
            return {
                'status': 'timeout',
                'script_path': script_path,
                'message': 'Script execution timed out.'
            }
        
        finally:
            # Optionally remove the temp file
            os.remove(script_path)


class VizAgent:
    def __init__(self, model, dataset_path="generated_dataset.csv"):
        import pandas as pd
        self.model = model
        self.dataset_path = dataset_path
        self.df = pd.read_csv(self.dataset_path)
        self.example = self.df.iloc[4]
        self.columns = self.df.columns



    def generate_viz_script(self):
        prompt = f"""
        You are a data visualization agent. Your job is to generate a complete Python script that:
        
        1️⃣ Loads the CSV dataset from the path: "{self.dataset_path}"  
        2️⃣ Creates a folder called "visualizations_current_date_time". the current date time part is dynamic, and you should find out what the current date and time is.
        3️⃣ Generates meaningful plots for all columns (e.g., histograms, scatterplots, boxplots, correlations where appropriate)  
        4️⃣ Saves each plot as a PNG in the "visualizations" folder, with clear filenames  
        5️⃣ Uses libraries like pandas, matplotlib, seaborn  
        6️⃣ Keeps the code clean, modular, and executable

        Information:
        1) Dataset columns : {self.columns}
        2) A row from the dataset for reference : {self.example}


        Output only the Python code without code fences or extra commentary.
        """

        response = self.model.generate_content(prompt)
        return response.text

