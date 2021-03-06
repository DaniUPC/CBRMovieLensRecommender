from utils import *
from case_base import CaseBase
from movies import FeedbackType

logger = get_logger()

class MovieRecommenderInterface(object):

    """ Interface for Movie Recommender """

    def retrieve(self, user_id):
        """ CBR retrieve cycle that retrieves similar users for the given user
        Args:
             user_id: Identifier of the query user
        Returns:
            users: List of identifiers of similar users
        """


    def reuse(self, user_id, neighbors):
        """ CBR reuse cycle that returns suitable movies to recommend to query user
        Args:
            user_id: Identifier of the query user
            neighbors: Identifier of the neighboring users
        Returns:
            movies: List of recommended movies for the user (CandidateInfo class)
        """


    def review(self, rated, recommended):
        """ CBR review cycle that evaluates the recommended movies. It resembles the user feedback
        done after the recommendation.
        Args:
            rated: RatedInfo class with the next rated movie recommended
            recommended: List of CandidateInfo objects representing the recommended movies
        Returns:
            recommended: List of recommended instances (FeedbackInfo class)
            retain_rated_case: Whether to retain input case or not
            mean_similarity: Mean similarity between rated movie and recommendations
        """


    def retain(self, rated_case, feedback_list, retain_rated_case):
        """ See base class
        Args:
           rated_case: RatingInfo about the reviewed case
           feedback_list: List of CandidateInfo containing feedback from thr review phase
           retain_rated_case: True / False value for saving the case to the CaseBase """


class MovieRecommender(MovieRecommenderInterface):

    def __init__(self,
                 path,
                 movies_per_neighbor=3,
                 rec_movies=5,
                 initial_affinity=0.5,
                 update_rate=0.1,
                 alpha=0.25,
                 beta=0.05,
                 gamma=0.55,
                 theta=0.15,
                 omega=0.15,
                 train_ratio=0.8,
                 shared_movies=8,
                 max_neighbors=5,
                 max_shared=6,
                 min_shared=3,
                 max_sim_threshold=1.50,
                 threshold_keep_movie=1,
                 movie_threshold=0.40,
                 high_similarity_treshold=0.55,
                 low_similarity_threshold=0.40,
                 update_value=1,
                 ratings_ratio=1.0):
        """ Constructor of the class
        Args:
            path: Path to MovieLens 1M dataset.
            movies_per_neighbor: Number of movies per neighbor to extract.
            rec_movies: Number of recommended movies for each query.
            initial_affinity: Initial affinity for users.
            update_rate: Pace at which we update the affinity of the users and the genre in recommendations.
            alpha: Weight for the user correlation in the movie score.
            beta: Weight for the popularity (mean rating in the system) in the movie score.
            gamma: Weight for the correlation of user preferences in the movie score.
            theta: Weight for the willigness of user preferences in the movie score.
            omega: Weight for the willigness of user affinity in the movie score.
            train_ratio: Fraction of ratings belonging to training.
            shared_movies: Number of top-rated movies from a user to use for computing his/her neighbors.
            max_neighbors: Maximum number of neighbors to compute for each user.
            max_shared: Maximum number of movies to be shared by a neighbor.
            min_shared: Minimum number of movies to be shared by a neighbor.
            max_sim_threshold: Maximum rating distance between movies to be considered shared between two users.
            threshold_keep_movie: Maximum difference for a case to be kept between a new movie rating
                and the mean system average.
            movie_threshold: Maximum distance between two movies to be considered similar.
            high_similarity_treshold: Minimum value of the mean rating of recommended movies for a case
                to be kept.
            low_similarity_threshold: Maximum value of the mean rating of recommended movies for a case
                to be kept.
            update_value: Number of cases that we need to process before updating the global stats.
            ratings_ratio: Ratio in interval (0, 1] of the original ratings to consider in the system.
        """
        self.cb = CaseBase(path,
                           initial_affinity=initial_affinity,
                           update_rate=update_rate,
                           alpha=alpha,
                           beta=beta,
                           gamma=gamma,
                           theta=theta,
                           omega=omega,
                           train_ratio=train_ratio,
                           ratings_ratio=ratings_ratio)
        self.cb.initialize()

        # Neighbor computation parameters
        self.shared_movies = shared_movies
        self.max_neighbors = max_neighbors
        self.max_shared = max_shared
        self.min_shared = min_shared
        self.max_sim_threshold = max_sim_threshold

        # Reuse phase parameters
        self.movies_per_neighbor = movies_per_neighbor
        self.rec_movies = rec_movies

        # Review phase parameters
        self.movie_thresh = movie_threshold
        self.threshold_keep_movie = threshold_keep_movie
        self.high_similarity_treshold = high_similarity_treshold
        self.low_similarity_threshold = low_similarity_threshold

        # Retain phase parameters
        self.N = 0  # Counter for test cases
        self.case_to_add = []
        self.update_value = update_value


    def _process_next_case(self):
        """ CBR cycle step for the given user for the given movie and rating """
        rated = self.cb.next_test_case()

        sim_users = self.retrieve(rated.user)  # Retrieves a set of user ids
        sim_movies = self.reuse(rated.user, neighbors=sim_users)  # Set of MovieInfo

        feedback, retain_rated_case, _ = self.review(rated, sim_movies)
        self.retain(rated, feedback, retain_rated_case)


    def test_cbr(self, test_size=100):
        """ Queries the test data into the CBR
        Args:
            test_size: Number of tests instances to use
        Returns
            scores: Mean movie score at each test iteration.
            sims: Mean similarity between rated and recommended item at each test iteration.
        """

        logger.info('Testing CBR ...')

        # Log values
        scores, sims = [], []

        # Iterate while there are cases left
        rated = self.cb.next_test_case()
        count = 1
        while rated is not None and count <= test_size:

            logger.info('Test iteration %i ...' % count)

            # RETRIEVE phase: get set of user ids
            sim_users = self.retrieve(rated.user)

            # REUSE phase: get set of candidate movies
            sim_movies = self.reuse(rated.user, neighbors=sim_users)

            # REVIEW phase: compare recommendations to rated movie
            feedback, retain_rated_case, mean_sim = self.review(rated, sim_movies)

            # RETAIN phase: retain information if needed
            self.retain(rated, feedback, retain_rated_case)

            # Store values for current iteration (scores from reuse and similarity from review)
            scores.append(np.mean([x.score for x in sim_movies]))
            sims.append(mean_sim)

            # Next case
            rated = self.cb.next_test_case()
            count += 1

        return scores, sims


    """ Implementations of the Recommender interface """


    def retrieve(self, user_id):
        """ See base class """
        logger.info("Retrieving phase for user %d" % user_id)

        # User candidates as those who has rated at least one movie in common with query
        candidates = self.cb.get_user_candidates(user_id,
                                                 num_movies=self.shared_movies,
                                                 num_neighs=self.max_neighbors,
                                                 max_k=self.max_shared,
                                                 min_k=self.min_shared,
                                                 sim_thresh=self.max_sim_threshold)

        # Get shared movies and correlation for candidates
        logger.info("Computing user similarities for %d users" % len(candidates))
        stats = [(c_id, self.cb.get_user_similarity(user_id, c_id)) for c_id in candidates]

        # Return top
        logger.info("Sorting user similarities")
        sorted_stats = sorted(stats, key=lambda tup: tup[1], reverse=True)[:self.max_neighbors]
        return sorted_stats


    def reuse(self, user_id, neighbors):
        """ See base class """

        logger.info("Reuse phase for user %d" % user_id)
        movies = []

        logger.info("Retrieved neighbors: {}".format([n[0] for n in neighbors]))

        if len(neighbors) == 0:
            # If no neighbors found, return popular movies
            unique_recommendations = self.cb.get_popular_candidates(user_id)
        else:
            # Iterate over retrieved neighbors to generate movie candidates
            for (neighbor_id, _) in neighbors:
                # Create a candidate for each unseen movies
                unseen_movies = self.cb.get_suggestions(user_id, neighbor_id, self.movies_per_neighbor)
                for m_id in unseen_movies:
                    candidate = self.cb.get_movie_candidate(movie_id=m_id, user_id=user_id, neigh_id=neighbor_id)
                    movies.append(candidate)

            # Unique recommendations
            dict_candidate = {}
            for m in movies:
                dict_candidate[m.movie] = m
            unique_recommendations = dict_candidate.values()

        # Return top movies
        return sorted(unique_recommendations, key=lambda x: x.score, reverse=True)[:self.rec_movies]


    def review(self, rated, recommended):
        """ See base class """
        logger.info("Review phase for user %d" % rated.user)

        # Print user preferences
        genres = self.cb.genres
        prefs = self.cb.get_user_preferences(rated.user)

        # Get rated metadata
        rated_name = self.cb._get_movie_name(rated.movie)
        rat = self.cb.get_mean_user_rating(recommended[0].user)
        logger.info("Rated movie {}({}) with {}, genres: {}"
                    .format(rated_name, rated.movie, rated.rating, self.cb._get_genre_categories(rated.movie)))
        logger.info("Mean rating of query user is %f, while mean movie rating for movie is %f"
                    % (rat,  self.cb.get_mean_movie_rating(rated.movie)))

        sum_similarity = 0
        # Fill feedback of recommendations
        for rec in recommended:

            # Calculating movie similarity between rated movie and recommended movie
            sim = self.cb.get_movie_similarity(rec.movie, rec.genres, rated.movie, rated.genres)

            sum_similarity = sum_similarity + sim

            if rec.movie == rated.movie and rated.rating > self.cb.get_mean_user_rating(rec.user):
                rec.feedback = FeedbackType.GOOD

            elif rec.movie == rated.movie and rated.rating <= self.cb.get_mean_user_rating(rec.user):
                rec.feedback = FeedbackType.BAD

            elif sim > self.movie_thresh:

                if rated.rating > self.cb.get_mean_user_rating(rec.user):
                    rec.feedback = FeedbackType.GOOD
                else:
                    rec.feedback = FeedbackType.BAD
            else:
                # Movie is different
                if rated.rating > self.cb.get_mean_user_rating(rec.user):
                    rec.feedback = FeedbackType.BAD
                else:
                    rec.feedback = FeedbackType.NEUTRAL

            logger.info("Recommended movie {}({}) has similarity {} with rated one. Feedback: {}"
                        .format(rec.name, rec.movie, sim, rec.feedback))
            logger.info("Movie {} has genres {}".format(rec.name, rec.genre_representation))

        # Compute mean similarity of recommendations
        mean_similarity = float(sum_similarity / len(recommended))

        logger.info("Mean similarity of recommended movies and rated movies is %f" % mean_similarity)

        # Check rating and mean similarity differs from expecteed values
        rating_diff_bool = abs(rated.rating - self.cb.get_mean_movie_rating(rated.movie)) > self.threshold_keep_movie
        non_redundant_bool = (mean_similarity > self.high_similarity_treshold) or \
                             (mean_similarity < self.low_similarity_threshold)
        retain_rated_case = rating_diff_bool and non_redundant_bool

        return recommended, retain_rated_case, mean_similarity


    def retain(self, rated_case, feedback_list, retain_rated_case):
        """ See base class """

        if retain_rated_case:

            logger.info("Case added for retaining")

            self.N += 1
            self.case_to_add.append(rated_case)

            if self.N == self.update_value:

                # Collect data for cases to
                users = [c.user for c in self.case_to_add]
                movies = [c.movie for c in self.case_to_add]
                ratings = [c.rating for c in self.case_to_add]
                timestamps = [c.timestamp for c in self.case_to_add]

                logger.info("Updating case base with cached retained information ...")

                # Update case base
                self.cb.update_case_base(users, movies, ratings, timestamps)

                # Reset values and empty rated case list
                self.N = 0
                self.case_to_add = []

                # Update CaseBase
                self.cb.update_popularity()
                self.cb.update_mean_movie_rating()

                self.cb.update_mean_user_rating()
        else:
            logger.info("Case not retained")

        logger.info("Updating user and genre willingness ...")
        user_id = rated_case.user
        for c in feedback_list:
            # Updating genre willingness of user_id depending on CandidateInfo object that was reviewed
            self.cb.update_genre_willigness(user_id, c)
            # Updating user affinity of user_id
            self.cb.update_user_affinity(user_id, c)

        return
