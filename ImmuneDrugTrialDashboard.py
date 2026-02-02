"""
Interactive Dashboard for Immune Drug Trial Analysis
Bob Loblaw - Loblaw Bio Clinical Trial Dashboard
"""

import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sqlite3
from scipy import stats

app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Immune Drug Trial Dashboard"

conn = sqlite3.connect("ImmuneDrugTrial.db")

subjects_df = pd.read_sql("SELECT * FROM Subjects ORDER BY subject", conn)
samples_df = pd.read_sql("SELECT * FROM Samples ORDER BY sample", conn)

cell_frequencies_df = pd.read_sql("""
    SELECT * FROM SampleCellFrequencies 
    ORDER BY sample, population
""", conn)

def get_cell_data(population):
    return pd.read_sql(f"""
        SELECT Subjects.response, SampleCellFrequencies.percentage
        FROM SampleCellFrequencies
        JOIN Samples ON Samples.sample = SampleCellFrequencies.sample
        JOIN Subjects ON Subjects.subject = Samples.subject
        WHERE Subjects.treatment = 'miraclib'
          AND Subjects.condition = 'melanoma'
          AND Samples.sample_type = 'PBMC'
          AND SampleCellFrequencies.population = '{population}'
    """, conn)

populations = ['b_cell', 'cd8_t_cell', 'cd4_t_cell', 'nk_cell', 'monocyte']
population_names = {
    'b_cell': 'B Cell',
    'cd8_t_cell': 'CD8 T Cell',
    'cd4_t_cell': 'CD4 T Cell',
    'nk_cell': 'NK Cell',
    'monocyte': 'Monocyte'
}

cell_data = {pop: get_cell_data(pop) for pop in populations}

stats_results = []
for pop in populations:
    df = cell_data[pop]
    responders = df.loc[df['response'] == 'yes', "percentage"]
    nonresponders = df.loc[df['response'] == 'no', "percentage"]
    
    t_stat, p_value = stats.ttest_ind(responders, nonresponders, equal_var=True)
    
    stats_results.append({
        'Cell Type': population_names[pop],
        'T-statistic': round(t_stat, 3),
        'P-value': round(p_value, 4),
        'Significant (p<0.05)': 'Yes' if p_value < 0.05 else 'No'
    })

stats_df = pd.DataFrame(stats_results)

filter_condition = """
Subjects.treatment = 'miraclib' AND
Subjects.condition = 'melanoma' AND
Samples.sample_type = 'PBMC' AND
Samples.time_from_treatment = 0
"""

baseline_samples = pd.read_sql(f"""
    SELECT Samples.sample, Subjects.subject, Subjects.project, 
           Subjects.response, Subjects.sex
    FROM Samples
    JOIN Subjects ON Subjects.subject = Samples.subject
    WHERE {filter_condition}
    ORDER BY Samples.sample
""", conn)

samples_per_project = pd.read_sql(f"""
    SELECT Subjects.project, COUNT(Samples.sample) AS num_samples
    FROM Samples
    JOIN Subjects ON Subjects.subject = Samples.subject
    WHERE {filter_condition}
    GROUP BY Subjects.project
""", conn)

subjects_per_response = pd.read_sql(f"""
    SELECT Subjects.response, COUNT(DISTINCT Subjects.subject) AS num_subjects
    FROM Samples
    JOIN Subjects ON Subjects.subject = Samples.subject
    WHERE {filter_condition}
    GROUP BY Subjects.response
""", conn)

subjects_per_sex = pd.read_sql(f"""
    SELECT Subjects.sex, COUNT(DISTINCT Subjects.subject) AS num_subjects
    FROM Samples
    JOIN Subjects ON Subjects.subject = Samples.subject
    WHERE {filter_condition}
    GROUP BY Subjects.sex
""", conn)

conn.close()

colors = {
    'background': '#f8f9fa',
    'card': '#ffffff',
    'primary': '#2c3e50',
    'secondary': '#3498db',
    'accent': '#e74c3c'
}

app.layout = html.Div(style={'backgroundColor': colors['background'], 'minHeight': '100vh', 'padding': '20px'}, children=[
    html.Div([
        html.H1("Immune Drug Trial Analysis Dashboard", 
                style={'textAlign': 'center', 'color': colors['primary'], 'marginBottom': '10px'}),
    ]),
    
    dcc.Tabs(id='tabs', value='tab-1', children=[
        dcc.Tab(label='Part 1: Data Management', value='tab-1', 
                style={'fontWeight': 'bold'}, selected_style={'fontWeight': 'bold', 'backgroundColor': colors['secondary'], 'color': 'white'}),
        dcc.Tab(label='Part 2: Initial Analysis - Data Overview', value='tab-2',
                style={'fontWeight': 'bold'}, selected_style={'fontWeight': 'bold', 'backgroundColor': colors['secondary'], 'color': 'white'}),
        dcc.Tab(label='Part 3: Statistical Analysis', value='tab-3',
                style={'fontWeight': 'bold'}, selected_style={'fontWeight': 'bold', 'backgroundColor': colors['secondary'], 'color': 'white'}),
        dcc.Tab(label='Part 4: Data Subset Analysis', value='tab-4',
                style={'fontWeight': 'bold'}, selected_style={'fontWeight': 'bold', 'backgroundColor': colors['secondary'], 'color': 'white'}),
    ]),
    
    html.Div(id='tabs-content', style={'marginTop': '20px'})
])

@app.callback(Output('tabs-content', 'children'),
              Input('tabs', 'value'))
def render_content(tab):
    if tab == 'tab-1':
        return html.Div([
            html.Div([
                html.H2("Subjects Table", style={'color': colors['primary']}),
                html.P(f"Total Subjects: {len(subjects_df)}", style={'fontSize': '16px', 'fontWeight': 'bold'}),
                dash_table.DataTable(
                    id='subjects-table',
                    columns=[{"name": i, "id": i} for i in subjects_df.columns],
                    data=subjects_df.to_dict('records'),
                    filter_action="native",
                    sort_action="native",
                    page_size=15,
                    style_table={'overflowX': 'auto'},
                    style_cell={
                        'textAlign': 'left',
                        'padding': '10px',
                        'fontFamily': 'Arial'
                    },
                    style_header={
                        'backgroundColor': colors['primary'],
                        'color': 'white',
                        'fontWeight': 'bold'
                    },
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': '#f9f9f9'
                        }
                    ]
                )
            ], style={'backgroundColor': colors['card'], 'padding': '20px', 'borderRadius': '10px', 'marginBottom': '20px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}),
            
            html.Div([
                html.H2("Samples Table", style={'color': colors['primary']}),
                html.P(f"Total Samples: {len(samples_df)}", style={'fontSize': '16px', 'fontWeight': 'bold'}),
                dash_table.DataTable(
                    id='samples-table',
                    columns=[{"name": i, "id": i} for i in samples_df.columns],
                    data=samples_df.to_dict('records'),
                    filter_action="native",
                    sort_action="native",
                    page_size=15,
                    style_table={'overflowX': 'auto'},
                    style_cell={
                        'textAlign': 'left',
                        'padding': '10px',
                        'fontFamily': 'Arial'
                    },
                    style_header={
                        'backgroundColor': colors['primary'],
                        'color': 'white',
                        'fontWeight': 'bold'
                    },
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': '#f9f9f9'
                        }
                    ]
                )
            ], style={'backgroundColor': colors['card'], 'padding': '20px', 'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'})
        ])
    
    elif tab == 'tab-2':
        return html.Div([
            html.H2("Cell Population Frequencies by Sample", style={'color': colors['primary']}),
            html.P("Relative frequency of each immune cell population as a percentage of total cells per sample", 
                   style={'fontSize': '14px', 'marginBottom': '20px'}),
            dash_table.DataTable(
                id='frequencies-table',
                columns=[{"name": i, "id": i, "type": "numeric", "format": {"specifier": ".2f"} if i == "percentage" else {}} 
                         for i in cell_frequencies_df.columns],
                data=cell_frequencies_df.to_dict('records'),
                filter_action="native",
                sort_action="native",
                page_size=20,
                style_table={'overflowX': 'auto'},
                style_cell={
                    'textAlign': 'left',
                    'padding': '10px',
                    'fontFamily': 'Arial'
                },
                style_header={
                    'backgroundColor': colors['primary'],
                    'color': 'white',
                    'fontWeight': 'bold'
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': '#f9f9f9'
                    },
                    {
                        'if': {'column_id': 'percentage'},
                        'fontWeight': 'bold',
                        'color': colors['secondary']
                    }
                ]
            )
        ], style={'backgroundColor': colors['card'], 'padding': '20px', 'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'})
    
    elif tab == 'tab-3':

        boxplot_figures = []
        for pop in populations:
            df = cell_data[pop]
            fig = px.box(df, x='response', y='percentage', 
                        title=f"{population_names[pop]} Relative Frequency by Drug Response",
                        labels={'response': 'Patient Responded to Drug', 
                               'percentage': f'{population_names[pop]} Relative Frequency (%)'},
                        color='response',
                        color_discrete_map={'yes': '#2ecc71', 'no': '#e74c3c'})
            
            fig.update_layout(
                plot_bgcolor='white',
                paper_bgcolor='white',
                font={'size': 12},
                showlegend=True,
                height=400
            )
            
            boxplot_figures.append(
                html.Div([
                    dcc.Graph(figure=fig)
                ], style={'marginBottom': '20px'})
            )
        
        return html.Div([
            html.H2("Statistical Analysis: Melanoma Patients on Miraclib (PBMC Samples)", 
                    style={'color': colors['primary']}),
            html.P("Comparing cell population frequencies between responders and non-responders", 
                   style={'fontSize': '14px', 'marginBottom': '20px'}),
            
            html.Div([
                html.H3("Statistical Test Results (Two-Sample t-test)", style={'color': colors['primary']}),
                dash_table.DataTable(
                    columns=[{"name": i, "id": i} for i in stats_df.columns],
                    data=stats_df.to_dict('records'),
                    style_cell={
                        'textAlign': 'center',
                        'padding': '12px',
                        'fontFamily': 'Arial'
                    },
                    style_header={
                        'backgroundColor': colors['primary'],
                        'color': 'white',
                        'fontWeight': 'bold'
                    },
                    style_data_conditional=[
                        {
                            'if': {
                                'filter_query': '{Significant (p<0.05)} = "Yes"',
                                'column_id': 'Significant (p<0.05)'
                            },
                            'backgroundColor': '#d4edda',
                            'color': '#155724',
                            'fontWeight': 'bold'
                        }
                    ]
                )
            ], style={'backgroundColor': colors['card'], 'padding': '20px', 'borderRadius': '10px', 
                     'marginBottom': '30px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}),
            
            html.Div([
                html.H3("Distribution Comparisons", style={'color': colors['primary'], 'marginBottom': '20px'}),
                *boxplot_figures
            ], style={'backgroundColor': colors['card'], 'padding': '20px', 'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'})
        ])
    
    elif tab == 'tab-4':
        fig1 = px.bar(samples_per_project, x='project', y='num_samples',
                     title='Samples per Project',
                     labels={'project': 'Project', 'num_samples': 'Number of Samples'},
                     color='num_samples',
                     color_continuous_scale='Blues')
        fig1.update_layout(plot_bgcolor='white', paper_bgcolor='white', showlegend=False)
        
        fig2 = px.bar(subjects_per_response, x='response', y='num_subjects',
                     title='Subjects by Response Status',
                     labels={'response': 'Response to Treatment', 'num_subjects': 'Number of Subjects'},
                     color='response',
                     color_discrete_map={'yes': '#2ecc71', 'no': '#e74c3c'})
        fig2.update_layout(plot_bgcolor='white', paper_bgcolor='white')
        
        fig3 = px.bar(subjects_per_sex, x='sex', y='num_subjects',
                     title='Subjects by Sex',
                     labels={'sex': 'Sex', 'num_subjects': 'Number of Subjects'},
                     color='sex',
                     color_discrete_map={'M': '#3498db', 'F': '#e74c3c'})
        fig3.update_layout(plot_bgcolor='white', paper_bgcolor='white')
        
        return html.Div([
            html.H2("Subset Analysis: Baseline Melanoma PBMC Samples (Miraclib Treatment)", 
                    style={'color': colors['primary']}),
            html.P("Analysis of samples at baseline (time_from_treatment = 0)", 
                   style={'fontSize': '14px', 'marginBottom': '20px'}),
            
            html.Div([
                html.H3(f"Baseline Samples (n={len(baseline_samples)})", style={'color': colors['primary']}),
                dash_table.DataTable(
                    columns=[{"name": i, "id": i} for i in baseline_samples.columns],
                    data=baseline_samples.to_dict('records'),
                    filter_action="native",
                    sort_action="native",
                    page_size=10,
                    style_cell={
                        'textAlign': 'left',
                        'padding': '10px',
                        'fontFamily': 'Arial'
                    },
                    style_header={
                        'backgroundColor': colors['primary'],
                        'color': 'white',
                        'fontWeight': 'bold'
                    },
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': '#f9f9f9'
                        }
                    ]
                )
            ], style={'backgroundColor': colors['card'], 'padding': '20px', 'borderRadius': '10px', 
                     'marginBottom': '20px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}),
            
            html.Div([
                html.H3("Summary Statistics", style={'color': colors['primary'], 'marginBottom': '20px'}),
                html.Div([
                    html.Div([dcc.Graph(figure=fig1)], style={'width': '33%', 'display': 'inline-block'}),
                    html.Div([dcc.Graph(figure=fig2)], style={'width': '33%', 'display': 'inline-block'}),
                    html.Div([dcc.Graph(figure=fig3)], style={'width': '33%', 'display': 'inline-block'}),
                ])
            ], style={'backgroundColor': colors['card'], 'padding': '20px', 'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'})
        ])

if __name__ == '__main__':
    print("\n" + "="*60)
    print("Immune Drug Trial Dashboard Starting...")
    print("="*60)
    print("\nDashboard Features:")
    print("  • Part 1: Browse and search Subjects & Samples tables")
    print("  • Part 2: View cell population frequencies")
    print("  • Part 3: Statistical analysis with boxplots")
    print("  • Part 4: Baseline sample subset analysis")
    print("\nOpening dashboard at: http://127.0.0.1:8050/")
    print("="*60 + "\n")
    
    app.run(debug=False, host='127.0.0.1', port=8050)