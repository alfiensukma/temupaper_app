from django_unicorn.components import UnicornView


class LoadingSkeletonView(UnicornView):
    skeleton_count: int = 6
    
    def get_skeleton_range(self):
        return range(self.skeleton_count)
