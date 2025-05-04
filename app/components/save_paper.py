from django_unicorn.components import UnicornView
from app.models import User, Paper, SavesPaperRel
import logging
from neomodel.exceptions import DoesNotExist
import datetime

logger = logging.getLogger(__name__)

class SavePaperView(UnicornView):
    is_saved = False
    paper_id = None
    message = ""
    saved_at = None
    
    def mount(self):
        if self.paper_id:
            try:
                user_id = self.request.session.get('user_id', '')
                
                if not user_id:
                    self.is_saved = False
                    return
                
                user = User.nodes.get(userId=user_id)
                paper = Paper.nodes.get_or_none(paperId=str(self.paper_id))
                
                if paper:

                    relationship = user.saves_papers.relationship(paper)
                    if relationship:
                        self.is_saved = True
                        self.saved_at = relationship.saved_at
                    else:
                        self.is_saved = False
                else:
                    self.is_saved = False
                
            except Exception as e:
                logger.error(f"Error checking saved status: {str(e)}")
                self.is_saved = False
    
    def save_paper(self):
        """Create or delete relationship between User and Paper nodes"""
        try:
            user_id = self.request.session.get('user_id', '')
            
            if not user_id:
                self.message = "Silakan login terlebih dahulu"
                return
            
            user = User.nodes.get(userId=user_id)
            
            try:
                paper = Paper.nodes.get(paperId=str(self.paper_id))
                created = False
            except DoesNotExist:
                paper = Paper(paperId=str(self.paper_id))
                paper.save()
                created = True
            
            if not self.is_saved:
                user.saves_papers.connect(paper, {'saved_at': datetime.datetime.now()})
                self.is_saved = True
                self.message = "Karya ilmiah berhasil disimpan!"
            else:
                user.saves_papers.disconnect(paper)
                self.is_saved = False
                self.message = "Karya ilmiah batal disimpan!"
                self.saved_at = None
                
        except Exception as e:
            logger.error(f"Error saving paper: {str(e)}")
            self.message = "Gagal menyimpan karya ilmiah"