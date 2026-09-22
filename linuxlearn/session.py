import json
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

class SessionManager:
    def __init__(self):
        self.session_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "interactions": []
        }
        self.session_dir = Path.home() / ".config" / "linuxlearn" / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def record(self, user_prompt: str, proposal: dict, executed: bool, success: bool):
        self.session_data["interactions"].append({
            "prompt": user_prompt,
            "proposal": proposal,
            "executed": executed,
            "success": success,
            "time": datetime.now().strftime("%H:%M:%S")
        })

    def export_notes(self) -> tuple[str, str]:
        if not self.session_data["interactions"]:
            return "", ""

        timestamp_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = self.session_dir / f"session_{timestamp_slug}.json"
        pdf_path = self.session_dir / f"linuxlearn_study_notes_{timestamp_slug}.pdf"

        # Export raw JSON log
        with open(json_path, "w") as f:
            json.dump(self.session_data, f, indent=4)

        # Build Professional PDF Study Notes using ReportLab
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            rightMargin=40, leftMargin=40,
            topMargin=40, bottomMargin=40
        )
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'DocTitle', parent=styles['Heading1'],
            fontSize=22, textColor=colors.HexColor("#1E293B"),
            spaceAfter=6, alignment=1
        )
        subtitle_style = ParagraphStyle(
            'DocSub', parent=styles['Normal'],
            fontSize=10, textColor=colors.HexColor("#64748B"),
            spaceAfter=20, alignment=1
        )
        heading_style = ParagraphStyle(
            'SectionHead', parent=styles['Heading2'],
            fontSize=12, textColor=colors.HexColor("#0F172A"),
            spaceBefore=10, spaceAfter=4
        )
        body_style = ParagraphStyle(
            'Body', parent=styles['Normal'],
            fontSize=10, textColor=colors.HexColor("#334155"),
            spaceAfter=6
        )
        code_style = ParagraphStyle(
            'CodeBlock', parent=styles['Normal'],
            fontSize=9, textColor=colors.HexColor("#047857"),
            fontName="Courier", spaceAfter=6
        )

        story = []
        story.append(Paragraph("LinuxLearn Terminal Study Notes", title_style))
        story.append(Paragraph(f"Session Date: {self.session_data['timestamp']} | Generated on Host Machine", subtitle_style))
        story.append(Spacer(1, 10))

        for idx, item in enumerate(self.session_data["interactions"], 1):
            prompt = item["prompt"]
            prop = item["proposal"]
            cmd = prop.get("command", "")
            exp = prop.get("explanation", "")
            concept = prop.get("concept", "General")
            
            story.append(Paragraph(f"Query {idx}: {prompt}", heading_style))
            story.append(Paragraph(f"<b>Core Concept:</b> {concept}", body_style))
            story.append(Paragraph(f"<b>Generated Command:</b> {cmd}", code_style))
            story.append(Paragraph(f"<b>Deconstruction & Application:</b> {exp}", body_style))
            
            # Word-by-word structural breakdown table
            words = cmd.split()
            if words:
                table_data = [["Token / Command Component", "Syntactic Role & Purpose"]]
                table_data.append([words[0], "Base executable command utility"])
                for w in words[1:]:
                    table_data.append([w, "Argument, flag, or structural path specifier"])
                
                t = Table(table_data, colWidths=[150, 350])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F1F5F9")),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#0F172A")),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0,0), (-1,0), 9),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1"))
                ]))
                story.append(Spacer(1, 4))
                story.append(t)
            
            story.append(Spacer(1, 15))

        doc.build(story)
        return str(json_path), str(pdf_path)