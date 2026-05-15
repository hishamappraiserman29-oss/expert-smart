"""
learning_platform.py — Learning Platform (Phase 35)

Training courses and certification management.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CourseLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class Course:
    course_id: str
    title: str
    description: str
    level: CourseLevel
    modules: int
    duration_hours: int
    instructor: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    has_certification: bool = True
    passing_score: float = 70.0
    prerequisites: List[str] = field(default_factory=list)
    learning_outcomes: List[str] = field(default_factory=list)
    lessons: List[str] = field(default_factory=list)
    is_published: bool = False
    enrollment_count: int = 0
    completion_count: int = 0
    average_rating: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "course_id": self.course_id,
            "title": self.title,
            "description": self.description,
            "level": self.level.value,
            "modules": self.modules,
            "duration_hours": self.duration_hours,
            "instructor": self.instructor,
            "has_certification": self.has_certification,
            "passing_score": self.passing_score,
            "is_published": self.is_published,
            "enrollment_count": self.enrollment_count,
            "completion_count": self.completion_count,
            "average_rating": round(self.average_rating, 2),
        }


@dataclass
class CourseEnrollment:
    enrollment_id: str
    user_id: str
    course_id: str
    enrolled_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress_percentage: float = 0.0
    modules_completed: int = 0
    quiz_scores: List[float] = field(default_factory=list)
    final_score: Optional[float] = None
    is_completed: bool = False
    has_certificate: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enrollment_id": self.enrollment_id,
            "user_id": self.user_id,
            "course_id": self.course_id,
            "enrolled_at": self.enrolled_at.isoformat(),
            "progress_percentage": round(self.progress_percentage, 2),
            "modules_completed": self.modules_completed,
            "final_score": self.final_score,
            "is_completed": self.is_completed,
            "has_certificate": self.has_certificate,
        }


class LearningPlatform:
    """Learning management system with courses, enrollments, and certifications."""

    def __init__(self) -> None:
        self.courses: Dict[str, Course] = {}
        self.enrollments: Dict[str, CourseEnrollment] = {}
        self._user_courses: Dict[str, List[str]] = {}
        self._lock = threading.Lock()
        logger.info("Learning Platform initialized")

    def create_course(
        self,
        course_id: str,
        title: str,
        description: str,
        level: CourseLevel,
        modules: int,
        duration_hours: int,
        instructor: str = "",
        has_certification: bool = True,
        passing_score: float = 70.0,
    ) -> Course:
        course = Course(
            course_id=course_id,
            title=title,
            description=description,
            level=level,
            modules=modules,
            duration_hours=duration_hours,
            instructor=instructor,
            has_certification=has_certification,
            passing_score=passing_score,
        )
        with self._lock:
            self.courses[course_id] = course
        logger.info("Course created: %s", title)
        return course

    def publish_course(self, course_id: str) -> bool:
        with self._lock:
            course = self.courses.get(course_id)
        if course is None:
            return False
        course.is_published = True
        return True

    def enroll_user(self, user_id: str, course_id: str) -> CourseEnrollment:
        with self._lock:
            course = self.courses.get(course_id)
        if course is None:
            raise ValueError(f"Course not found: {course_id}")

        enrollment_id = f"ENR-{user_id}-{course_id}-{int(datetime.utcnow().timestamp())}"
        enrollment = CourseEnrollment(
            enrollment_id=enrollment_id,
            user_id=user_id,
            course_id=course_id,
        )
        with self._lock:
            self.enrollments[enrollment_id] = enrollment
            self._user_courses.setdefault(user_id, []).append(course_id)
            course.enrollment_count += 1

        logger.info("User %s enrolled in %s", user_id, course_id)
        return enrollment

    def update_progress(self, enrollment_id: str, progress_pct: float, modules_done: int = 0) -> bool:
        with self._lock:
            enrollment = self.enrollments.get(enrollment_id)
        if enrollment is None:
            return False
        enrollment.progress_percentage = min(100.0, max(0.0, progress_pct))
        enrollment.modules_completed = modules_done
        if enrollment.started_at is None:
            enrollment.started_at = datetime.utcnow()
        return True

    def complete_course(self, enrollment_id: str, final_score: float) -> bool:
        with self._lock:
            enrollment = self.enrollments.get(enrollment_id)
        if enrollment is None:
            return False

        enrollment.final_score = final_score
        enrollment.completed_at = datetime.utcnow()
        enrollment.progress_percentage = 100.0

        with self._lock:
            course = self.courses.get(enrollment.course_id)

        if course and final_score >= course.passing_score:
            enrollment.is_completed = True
            enrollment.has_certificate = course.has_certification
            with self._lock:
                course.completion_count += 1
            logger.info("Course completed: %s (%.1f%%)", enrollment_id, final_score)
            return True

        logger.warning("Course not passed: %s (%.1f%% < %.1f%%)",
                       enrollment_id, final_score, course.passing_score if course else 70.0)
        return False

    def get_user_enrollments(self, user_id: str) -> List[CourseEnrollment]:
        with self._lock:
            return [e for e in self.enrollments.values() if e.user_id == user_id]

    def get_user_certificates(self, user_id: str) -> List[Dict[str, Any]]:
        certs: List[Dict[str, Any]] = []
        for enrollment in self.get_user_enrollments(user_id):
            if enrollment.has_certificate:
                with self._lock:
                    course = self.courses.get(enrollment.course_id)
                certs.append({
                    "certificate_id": enrollment.enrollment_id,
                    "course_id": enrollment.course_id,
                    "course_title": course.title if course else "Unknown",
                    "completed_at": enrollment.completed_at.isoformat() if enrollment.completed_at else None,
                    "score": enrollment.final_score,
                })
        return certs

    def get_platform_statistics(self) -> Dict[str, Any]:
        with self._lock:
            enrollments = list(self.enrollments.values())
            n_enroll = len(enrollments)
            completions = sum(1 for e in enrollments if e.is_completed)
            certs = sum(1 for e in enrollments if e.has_certificate)
            users = len(self._user_courses)
            courses = list(self.courses.values())
        return {
            "total_courses": len(courses),
            "published_courses": sum(1 for c in courses if c.is_published),
            "total_enrollments": n_enroll,
            "completions": completions,
            "completion_rate": round(completions / n_enroll * 100, 2) if n_enroll > 0 else 0.0,
            "certificates_issued": certs,
            "unique_users": users,
        }

    def count_courses(self) -> int:
        with self._lock:
            return len(self.courses)

    def count_enrollments(self) -> int:
        with self._lock:
            return len(self.enrollments)


learning_platform = LearningPlatform()
