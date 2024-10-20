with app.app_context():
  feedback_giver = FeedbackGiver.query.filter_by(token="f8f086c9-1323-4db9-aee9-fef340136c6c").first()
  if feedback_giver:
      print("Token found:", feedback_giver)
  else:
      print("Token not found in FeedbackGiver")