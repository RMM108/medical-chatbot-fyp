"""
Progress Visualization Module
Creates interactive charts for student performance tracking
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime
from typing import Dict, List
from database import StudentDatabase

class ProgressVisualizer:
    """Generate interactive visualizations for student progress"""
    
    def __init__(self, db: StudentDatabase):
        self.db = db
        
        # Color scheme
        self.colors = {
            'primary': '#4F46E5',      # Indigo
            'success': '#10B981',      # Green
            'warning': '#F59E0B',      # Amber
            'danger': '#EF4444',       # Red
            'info': '#3B82F6',         # Blue
            'purple': '#8B5CF6',       # Purple
        }
    
    def create_progress_timeline(self, student_id: int) -> go.Figure:
        """
        Create line chart showing score progression over time
        Shows overall score, diagnostic accuracy, and empathy score
        """
        progress_data = self.db.get_progress_data(student_id)
        timeline = progress_data['progress_timeline']
        
        if not timeline:
            return self._create_empty_chart("No sessions yet", 
                                           "Complete some interviews to see your progress!")
        
        # Convert to DataFrame
        df = pd.DataFrame(timeline)
        df['date'] = pd.to_datetime(df['date'])
        df['session_number'] = range(1, len(df) + 1)
        
        # Create figure
        fig = go.Figure()
        
        # Overall Score line
        fig.add_trace(go.Scatter(
            x=df['session_number'],
            y=df['overall_score'],
            name='Overall Score',
            mode='lines+markers',
            line=dict(color=self.colors['primary'], width=3),
            marker=dict(size=8),
            hovertemplate='<b>Session %{x}</b><br>Score: %{y:.1f}%<extra></extra>'
        ))
        
        # Diagnostic Accuracy line
        fig.add_trace(go.Scatter(
            x=df['session_number'],
            y=df['diagnostic_accuracy'],
            name='Diagnostic Accuracy',
            mode='lines+markers',
            line=dict(color=self.colors['success'], width=2, dash='dash'),
            marker=dict(size=6),
            hovertemplate='<b>Session %{x}</b><br>Diagnostic: %{y:.1f}%<extra></extra>'
        ))
        
        # Empathy Score line
        fig.add_trace(go.Scatter(
            x=df['session_number'],
            y=df['empathy_score'],
            name='Empathy Score',
            mode='lines+markers',
            line=dict(color=self.colors['purple'], width=2, dash='dot'),
            marker=dict(size=6),
            hovertemplate='<b>Session %{x}</b><br>Empathy: %{y:.1f}%<extra></extra>'
        ))
        
        # Add trend line for overall score
        if len(df) > 2:
            from scipy import stats
            slope, intercept, r_value, p_value, std_err = stats.linregress(
                df['session_number'], df['overall_score']
            )
            trend_line = slope * df['session_number'] + intercept
            
            fig.add_trace(go.Scatter(
                x=df['session_number'],
                y=trend_line,
                name='Trend',
                mode='lines',
                line=dict(color='gray', width=1, dash='dash'),
                opacity=0.5,
                hovertemplate='Trend: %{y:.1f}%<extra></extra>'
            ))
        
        # Layout
        fig.update_layout(
            title={
                'text': '📈 Performance Progress Over Time',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20}
            },
            xaxis_title='Session Number',
            yaxis_title='Score (%)',
            hovermode='x unified',
            template='plotly_white',
            height=500,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            yaxis=dict(range=[0, 105])
        )
        
        return fig
    
    def create_skills_radar(self, student_id: int) -> go.Figure:
        """
        Create radar/spider chart showing skills breakdown
        Latest session vs average
        """
        sessions = self.db.get_student_sessions(student_id, limit=1)
        
        if not sessions or not sessions[0]['overall_score']:
            return self._create_empty_chart("No evaluations yet",
                                           "Complete an interview to see skill breakdown")
        
        latest_session = sessions[0]
        session_details = self.db.get_session_details(latest_session['session_id'])
        
        if not session_details or not session_details['evaluation']:
            return self._create_empty_chart("No evaluation data", 
                                           "Evaluation not available for this session")
        
        evaluation = session_details['evaluation']
        empathy = evaluation.get('empathy_evaluation', {})
        
        # Skills data
        categories = [
            'Diagnostic<br>Accuracy',
            'Understanding<br>Pain',
            'Communicating<br>Understanding',
            'Intention<br>to Help',
            'Overall<br>Empathy'
        ]
        
        latest_scores = [
            evaluation.get('phq9_evaluation', {}).get('diagnostic_accuracy', 0),
            empathy.get('understanding', {}).get('score', 0),
            empathy.get('communication', {}).get('score', 0),
            empathy.get('intention', {}).get('score', 0),
            empathy.get('overall_score', 0)
        ]
        
        # Get average scores
        progress_data = self.db.get_progress_data(student_id)
        avg_scores = [
            progress_data['avg_diagnostic'],
            progress_data['avg_empathy'],  # Using overall empathy as proxy
            progress_data['avg_empathy'],
            progress_data['avg_empathy'],
            progress_data['avg_empathy']
        ]
        
        fig = go.Figure()
        
        # Latest session
        fig.add_trace(go.Scatterpolar(
            r=latest_scores,
            theta=categories,
            fill='toself',
            name='Latest Session',
            line=dict(color=self.colors['primary'], width=2),
            fillcolor=f"rgba(79, 70, 229, 0.2)"
        ))
        
        # Average
        if progress_data['total_sessions'] > 1:
            fig.add_trace(go.Scatterpolar(
                r=avg_scores,
                theta=categories,
                fill='toself',
                name='Your Average',
                line=dict(color=self.colors['success'], width=2, dash='dash'),
                fillcolor=f"rgba(16, 185, 129, 0.1)"
            ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )
            ),
            title={
                'text': '🎯 Skills Breakdown',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20}
            },
            showlegend=True,
            height=500,
            template='plotly_white'
        )
        
        return fig
    
    def create_severity_performance(self, student_id: int) -> go.Figure:
        """
        Bar chart showing performance across different severity levels
        """
        progress_data = self.db.get_progress_data(student_id)
        by_severity = progress_data['performance_by_severity']
        
        if not by_severity:
            return self._create_empty_chart("No severity data",
                                           "Practice with different severity levels")
        
        # Prepare data
        severities = ['Minimal', 'Mild', 'Moderate', 'Moderately Severe', 'Severe']
        counts = []
        avg_scores = []
        
        for severity in severities:
            data = by_severity.get(severity, {'count': 0, 'avg_score': 0})
            counts.append(data['count'])
            avg_scores.append(data['avg_score'] if data['avg_score'] else 0)
        
        # Create subplots
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('Sessions by Severity', 'Avg Score by Severity'),
            specs=[[{'type': 'bar'}, {'type': 'bar'}]]
        )
        
        # Sessions count
        fig.add_trace(
            go.Bar(
                x=severities,
                y=counts,
                name='Sessions',
                marker_color=self.colors['info'],
                text=counts,
                textposition='auto',
                hovertemplate='<b>%{x}</b><br>Sessions: %{y}<extra></extra>'
            ),
            row=1, col=1
        )
        
        # Average scores with color gradient
        colors_scale = []
        for score in avg_scores:
            if score >= 80:
                colors_scale.append(self.colors['success'])
            elif score >= 60:
                colors_scale.append(self.colors['warning'])
            else:
                colors_scale.append(self.colors['danger'])
        
        fig.add_trace(
            go.Bar(
                x=severities,
                y=avg_scores,
                name='Avg Score',
                marker_color=colors_scale,
                text=[f'{s:.1f}%' for s in avg_scores],
                textposition='auto',
                hovertemplate='<b>%{x}</b><br>Avg Score: %{y:.1f}%<extra></extra>'
            ),
            row=1, col=2
        )
        
        fig.update_layout(
            title={
                'text': '📊 Performance by Patient Severity',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20}
            },
            showlegend=False,
            height=400,
            template='plotly_white'
        )
        
        fig.update_xaxes(title_text="Severity Level", row=1, col=1)
        fig.update_xaxes(title_text="Severity Level", row=1, col=2)
        fig.update_yaxes(title_text="Number of Sessions", row=1, col=1)
        fig.update_yaxes(title_text="Average Score (%)", range=[0, 105], row=1, col=2)
        
        return fig
    
    def create_score_distribution(self, student_id: int) -> go.Figure:
        """
        Histogram showing distribution of scores
        """
        sessions = self.db.get_student_sessions(student_id, limit=100)
        
        if not sessions:
            return self._create_empty_chart("No sessions",
                                           "Complete interviews to see score distribution")
        
        scores = [s['overall_score'] for s in sessions if s['overall_score']]
        
        if not scores:
            return self._create_empty_chart("No scores yet",
                                           "Complete evaluations to see distribution")
        
        fig = go.Figure()
        
        fig.add_trace(go.Histogram(
            x=scores,
            nbinsx=10,
            marker_color=self.colors['primary'],
            opacity=0.7,
            name='Score Distribution',
            hovertemplate='Score Range: %{x}<br>Count: %{y}<extra></extra>'
        ))
        
        # Add mean line
        mean_score = sum(scores) / len(scores)
        fig.add_vline(
            x=mean_score,
            line_dash="dash",
            line_color=self.colors['danger'],
            annotation_text=f"Average: {mean_score:.1f}%",
            annotation_position="top"
        )
        
        fig.update_layout(
            title={
                'text': '📊 Score Distribution',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20}
            },
            xaxis_title='Score (%)',
            yaxis_title='Number of Sessions',
            template='plotly_white',
            height=400,
            showlegend=False
        )
        
        return fig
    
    def create_dashboard_summary(self, student_id: int) -> go.Figure:
        """
        Create summary dashboard with key metrics
        """
        progress_data = self.db.get_progress_data(student_id)
        sessions = self.db.get_student_sessions(student_id, limit=5)
        
        # Calculate improvement (first vs latest)
        if len(sessions) >= 2:
            latest = sessions[0]['overall_score'] or 0
            first = sessions[-1]['overall_score'] or 0
            improvement = latest - first
        else:
            improvement = 0
        
        # Create gauge charts for key metrics
        fig = make_subplots(
            rows=2, cols=2,
            specs=[
                [{'type': 'indicator'}, {'type': 'indicator'}],
                [{'type': 'indicator'}, {'type': 'indicator'}]
            ],
            subplot_titles=(
                'Overall Score',
                'Diagnostic Accuracy',
                'Empathy Score',
                'Improvement'
            )
        )
        
        # Overall Score
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=progress_data['avg_overall_score'],
            title={'text': "Overall"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': self.colors['primary']},
                'steps': [
                    {'range': [0, 60], 'color': "lightgray"},
                    {'range': [60, 80], 'color': "gray"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 80
                }
            }
        ), row=1, col=1)
        
        # Diagnostic Accuracy
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=progress_data['avg_diagnostic'],
            title={'text': "Diagnostic"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': self.colors['success']},
                'steps': [
                    {'range': [0, 60], 'color': "lightgray"},
                    {'range': [60, 80], 'color': "gray"}
                ]
            }
        ), row=1, col=2)
        
        # Empathy Score
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=progress_data['avg_empathy'],
            title={'text': "Empathy"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': self.colors['purple']},
                'steps': [
                    {'range': [0, 60], 'color': "lightgray"},
                    {'range': [60, 80], 'color': "gray"}
                ]
            }
        ), row=2, col=1)
        
        # Improvement
        fig.add_trace(go.Indicator(
            mode="number+delta",
            value=improvement,
            title={'text': "Improvement"},
            delta={'reference': 0, 'valueformat': '.1f'},
            number={'suffix': '%'}
        ), row=2, col=2)
        
        fig.update_layout(
            height=600,
            title={
                'text': f'📊 Performance Dashboard ({progress_data["total_sessions"]} sessions)',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 24}
            },
            template='plotly_white'
        )
        
        return fig
    
    def _create_empty_chart(self, title: str, message: str) -> go.Figure:
        """Create placeholder chart for empty data"""
        fig = go.Figure()
        
        fig.add_annotation(
            text=f"<b>{title}</b><br><br>{message}",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16)
        )
        
        fig.update_layout(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            height=400,
            template='plotly_white'
        )
        
        return fig
    
    def export_chart_html(self, fig: go.Figure, filename: str):
        """Export chart as standalone HTML file"""
        fig.write_html(filename)
        print(f"✓ Chart exported to {filename}")

# Demo/Testing
# Demo/Testing
if __name__ == "__main__":
    from database import StudentDatabase
    
    db = StudentDatabase()
    viz = ProgressVisualizer(db)
    
    # --- CHANGED: Set target student ID here ---
    target_student_id = 2 
    print(f"Generating charts for Student ID: {target_student_id}...")
    
    # Pass the variable to your methods
    timeline = viz.create_progress_timeline(target_student_id)
    skills = viz.create_skills_radar(target_student_id)
    severity = viz.create_severity_performance(target_student_id)
    
    # Display the result
    timeline.show()
    # skills.show() # Uncomment to see other charts
    
    print("\n✓ Charts generated for Student 2!")