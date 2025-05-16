from .models import Reward, Points
from django.db.models import Sum

def child_reward_context(request):
    if request.user.is_authenticated and request.user.role == 'child':
        active_reward = Reward.objects.filter(user=request.user, is_active=True).first()
        earned_points = 0
        reward_achieved = False

        if active_reward:
            earned_points = (
                Points.objects
                .filter(user=request.user, awarded_at__gte=active_reward.created_at)
                .aggregate(total=Sum('points'))['total'] or 0
            )
            reward_achieved = earned_points >= active_reward.points_required

        return {
            'active_reward': active_reward,
            'earned_points': earned_points,
            'reward_achieved': reward_achieved,
        }

    return {}
